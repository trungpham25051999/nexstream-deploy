# C4 model — text reference

**L1 Context**: NexStream is the telemetry platform used by Device and Query Client actors. Device sends telemetry; Query Client reads analytics. Test Publisher replaces devices in test environments.

**L2 Containers**: L4 TCP Load Balancer; C++ Ingest Gateway; Kafka/Redpanda; ClickHouse; C++ Processor; C++ Query API; metrics infrastructure. `nexstream-contracts` and `nexstream-deploy` are source repositories, **not** running containers.

**L3 Ingest Components**: Bootstrap/Configuration -> TCP Acceptor -> EpollReactor/Connection state -> Frame Decoder -> Protobuf Adapter -> IngestTelemetry use case -> Domain TelemetryValidator -> MessageProducer port -> KafkaProducer adapter. Delivery reports reach ACK Coordinator -> TCP output buffer. Explicit backpressure limits apply to frame buffers and Kafka pending bytes.

**Deployment**: local: one instance of each essential service, one Redpanda broker, one ClickHouse. Reference multi-node: LB HA, replicated Gateways, multi-broker Kafka with suitable replication and rack placement, ClickHouse HA/sharding according to observed workload. Replicas on a single physical host are not hardware HA.

**Diagram editing**: The `.drawio` model should mirror this baseline and be reviewed alongside ADRs. Do not treat a conceptual arrow as a claim that a protocol or data contract is implemented.
