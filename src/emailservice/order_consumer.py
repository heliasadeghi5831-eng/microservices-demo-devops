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


def required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"environment variable {name} is required")
    return value


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

    channel.queue_declare(
        queue=QUEUE,
        durable=True,
    )

    channel.queue_bind(
        exchange=EXCHANGE,
        queue=QUEUE,
        routing_key=ROUTING_KEY,
    )

    channel.basic_qos(prefetch_count=1)

    email_channel = grpc.insecure_channel(email_service_addr)
    email_stub = demo_pb2_grpc.EmailServiceStub(email_channel)

    def handle_message(ch, method, properties, body):
        event_id = properties.message_id or "unknown"

        request = demo_pb2.SendOrderConfirmationRequest()

        try:
            request.ParseFromString(body)

            logger.info(
                "processing OrderCreated event_id=%s order_id=%s email=%s",
                event_id,
                request.order.order_id,
                request.email,
            )

            email_stub.SendOrderConfirmation(request, timeout=10)

            ch.basic_ack(delivery_tag=method.delivery_tag)

            logger.info(
                "OrderCreated acknowledged event_id=%s order_id=%s",
                event_id,
                request.order.order_id,
            )

        except Exception:
            logger.exception(
                "OrderCreated processing failed event_id=%s; requeueing",
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
        "consumer started queue=%s email_service=%s",
        QUEUE,
        email_service_addr,
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