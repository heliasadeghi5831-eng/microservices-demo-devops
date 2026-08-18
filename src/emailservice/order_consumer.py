import logging
import os
import time

import grpc
import pika

import demo_pb2
import demo_pb2_grpc


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("order-confirmation-consumer")

EXCHANGE = "orders"
QUEUE = "order-confirmation"
ROUTING_KEY = "order.created.email"

RETRY_EXCHANGE = "orders.retry"
RETRY_QUEUE = "order-confirmation.retry"
RETRY_ROUTING_KEY = "order.created.email.retry"

DLX_EXCHANGE = "orders.dlx"
DLQ = "order-confirmation.dlq"
DLQ_ROUTING_KEY = "order.created.email.dlq"

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY_MS = int(os.getenv("RETRY_DELAY_MS", "5000"))


def required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"environment variable {name} is required")
    return value


def republish_properties(properties, retry_count):
    headers = dict(properties.headers or {})
    headers["x-retry-count"] = retry_count

    return pika.BasicProperties(
        content_type=properties.content_type,
        content_encoding=properties.content_encoding,
        headers=headers,
        delivery_mode=2,
        correlation_id=properties.correlation_id,
        message_id=properties.message_id,
        type=properties.type,
        app_id=properties.app_id,
    )


def consume():
    rabbit_host = required_env("RABBITMQ_HOST")
    rabbit_port = int(os.getenv("RABBITMQ_PORT", "5672"))
    rabbit_user = required_env("RABBITMQ_USER")
    rabbit_password = required_env("RABBITMQ_PASSWORD")
    email_service_addr = required_env("EMAIL_SERVICE_ADDR")

    credentials = pika.PlainCredentials(rabbit_user, rabbit_password)

    parameters = pika.ConnectionParameters(
        host=rabbit_host,
        port=rabbit_port,
        virtual_host="/",
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
        connection_attempts=10,
        retry_delay=3,
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="direct",
        durable=True,
    )

    channel.exchange_declare(
        exchange=RETRY_EXCHANGE,
        exchange_type="direct",
        durable=True,
    )

    channel.exchange_declare(
        exchange=DLX_EXCHANGE,
        exchange_type="direct",
        durable=True,
    )

    channel.queue_declare(
        queue=QUEUE,
        durable=True,
    )

    channel.queue_bind(
        exchange=EXCHANGE,
        queue=QUEUE,
        routing_key=ROUTING_KEY,
    )

    channel.queue_declare(
        queue=RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": RETRY_DELAY_MS,
            "x-dead-letter-exchange": EXCHANGE,
            "x-dead-letter-routing-key": ROUTING_KEY,
        },
    )

    channel.queue_bind(
        exchange=RETRY_EXCHANGE,
        queue=RETRY_QUEUE,
        routing_key=RETRY_ROUTING_KEY,
    )

    channel.queue_declare(
        queue=DLQ,
        durable=True,
    )

    channel.queue_bind(
        exchange=DLX_EXCHANGE,
        queue=DLQ,
        routing_key=DLQ_ROUTING_KEY,
    )

    # Publisher confirms are used before ACKing the original message.
    channel.confirm_delivery()

    channel.basic_qos(prefetch_count=1)

    email_channel = grpc.insecure_channel(email_service_addr)
    email_stub = demo_pb2_grpc.EmailServiceStub(email_channel)

    def handle_message(ch, method, properties, body):
        event_id = properties.message_id or "unknown"
        headers = dict(properties.headers or {})
        retry_count = int(headers.get("x-retry-count", 0))

        request = demo_pb2.SendOrderConfirmationRequest()
        order_id = "unknown"

        try:
            request.ParseFromString(body)
            order_id = request.order.order_id or "unknown"

            logger.info(
                "processing OrderCreated event_id=%s order_id=%s "
                "email=%s retry=%d/%d",
                event_id,
                order_id,
                request.email,
                retry_count,
                MAX_RETRIES,
            )

            email_stub.SendOrderConfirmation(request, timeout=10)

            ch.basic_ack(delivery_tag=method.delivery_tag)

            logger.info(
                "OrderCreated acknowledged event_id=%s order_id=%s",
                event_id,
                order_id,
            )

        except Exception:
            logger.exception(
                "OrderCreated processing failed event_id=%s "
                "order_id=%s retry=%d/%d",
                event_id,
                order_id,
                retry_count,
                MAX_RETRIES,
            )

            try:
                if retry_count < MAX_RETRIES:
                    next_retry = retry_count + 1

                    ch.basic_publish(
                        exchange=RETRY_EXCHANGE,
                        routing_key=RETRY_ROUTING_KEY,
                        body=body,
                        properties=republish_properties(
                            properties,
                            next_retry,
                        ),
                        mandatory=True,
                    )

                    ch.basic_ack(delivery_tag=method.delivery_tag)

                    logger.warning(
                        "OrderCreated scheduled for retry "
                        "event_id=%s attempt=%d/%d delay_ms=%d",
                        event_id,
                        next_retry,
                        MAX_RETRIES,
                        RETRY_DELAY_MS,
                    )

                else:
                    ch.basic_publish(
                        exchange=DLX_EXCHANGE,
                        routing_key=DLQ_ROUTING_KEY,
                        body=body,
                        properties=republish_properties(
                            properties,
                            retry_count,
                        ),
                        mandatory=True,
                    )

                    ch.basic_ack(delivery_tag=method.delivery_tag)

                    logger.error(
                        "OrderCreated moved to DLQ "
                        "event_id=%s retries=%d",
                        event_id,
                        retry_count,
                    )

            except Exception:
                logger.exception(
                    "Failed to route failed message event_id=%s; "
                    "requeueing original",
                    event_id,
                )

                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True,
                )

    channel.basic_consume(
        queue=QUEUE,
        on_message_callback=handle_message,
        auto_ack=False,
    )

    logger.info(
        "consumer started queue=%s retry_queue=%s dlq=%s "
        "email_service=%s max_retries=%d retry_delay_ms=%d",
        QUEUE,
        RETRY_QUEUE,
        DLQ,
        email_service_addr,
        MAX_RETRIES,
        RETRY_DELAY_MS,
    )

    channel.start_consuming()


def main():
    while True:
        try:
            consume()
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("consumer connection failed; retrying")
            time.sleep(5)


if __name__ == "__main__":
    main()
