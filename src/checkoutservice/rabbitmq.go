package main

import (
	"context"
	"fmt"
	"net/url"
	"sync"
	"time"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/checkoutservice/genproto"
	"github.com/google/uuid"
	amqp "github.com/rabbitmq/amqp091-go"
	"google.golang.org/protobuf/proto"
)

const (
	orderExchange   = "orders"
	orderQueue      = "order-confirmation"
	orderRoutingKey = "order.created.email"
)

type orderPublisher struct {
	mu   sync.Mutex
	uri  string
	conn *amqp.Connection
	ch   *amqp.Channel
}

func newOrderPublisher(addr, username, password string) *orderPublisher {
	u := &url.URL{
		Scheme: "amqp",
		User:   url.UserPassword(username, password),
		Host:   addr,
		Path:   "/",
	}

	return &orderPublisher{uri: u.String()}
}

func (p *orderPublisher) ensureChannel() error {
	if p.conn != nil && !p.conn.IsClosed() && p.ch != nil {
		return nil
	}

	p.closeLocked()

	conn, err := amqp.Dial(p.uri)
	if err != nil {
		return fmt.Errorf("connect to RabbitMQ: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return fmt.Errorf("open RabbitMQ channel: %w", err)
	}

	if err := ch.ExchangeDeclare(
		orderExchange,
		"direct",
		true,
		false,
		false,
		false,
		nil,
	); err != nil {
		ch.Close()
		conn.Close()
		return fmt.Errorf("declare exchange: %w", err)
	}

	queue, err := ch.QueueDeclare(
		orderQueue,
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		ch.Close()
		conn.Close()
		return fmt.Errorf("declare queue: %w", err)
	}

	if err := ch.QueueBind(
		queue.Name,
		orderRoutingKey,
		orderExchange,
		false,
		nil,
	); err != nil {
		ch.Close()
		conn.Close()
		return fmt.Errorf("bind queue: %w", err)
	}

	if err := ch.Confirm(false); err != nil {
		ch.Close()
		conn.Close()
		return fmt.Errorf("enable publisher confirms: %w", err)
	}

	p.conn = conn
	p.ch = ch

	return nil
}

func (p *orderPublisher) PublishOrderCreated(
	ctx context.Context,
	email string,
	order *pb.OrderResult,
) (string, error) {
	body, err := proto.Marshal(&pb.SendOrderConfirmationRequest{
		Email: email,
		Order: order,
	})
	if err != nil {
		return "", fmt.Errorf("marshal OrderCreated payload: %w", err)
	}

	eventID := uuid.NewString()

	p.mu.Lock()
	defer p.mu.Unlock()

	var lastErr error

	for attempt := 1; attempt <= 2; attempt++ {
		if err := p.ensureChannel(); err != nil {
			lastErr = err
			p.closeLocked()
			continue
		}

		publishCtx, cancel := context.WithTimeout(ctx, 5*time.Second)

		confirmation, err := p.ch.PublishWithDeferredConfirmWithContext(
			publishCtx,
			orderExchange,
			orderRoutingKey,
			true,
			false,
			amqp.Publishing{
				ContentType:   "application/x-protobuf",
				DeliveryMode:  amqp.Persistent,
				MessageId:     eventID,
				CorrelationId: order.GetOrderId(),
				Type:          "OrderCreated",
				Timestamp:     time.Now().UTC(),
				Body:          body,
			},
		)

		if err != nil {
			cancel()
			lastErr = fmt.Errorf("publish OrderCreated: %w", err)
			p.closeLocked()
			continue
		}

		acked, err := confirmation.WaitContext(publishCtx)
		cancel()

		if err != nil {
			lastErr = fmt.Errorf("wait for publisher confirm: %w", err)
			p.closeLocked()
			continue
		}

		if !acked {
			lastErr = fmt.Errorf("RabbitMQ nacked OrderCreated event %s", eventID)
			p.closeLocked()
			continue
		}

		return eventID, nil
	}

	return "", fmt.Errorf("OrderCreated publish failed after retry: %w", lastErr)
}

func (p *orderPublisher) closeLocked() {
	if p.ch != nil {
		_ = p.ch.Close()
		p.ch = nil
	}

	if p.conn != nil {
		_ = p.conn.Close()
		p.conn = nil
	}
}
