# ■ Postgresql

```bash
./bin/postgresql.sh

# ログのtail
docker logs -f ${PROJECT_NAME}-sample-postgresql
```

## 動作確認

```bash
CONTAINER_NAME=${PROJECT_NAME}-sample-postgresql

# appユーザーでログイン
PGPASSWORD=root1234 psql -U app -h ${CONTAINER_NAME} -d sample -p 5432
```


---



# ■ MySQL

```bash
./bin/mysql.sh

# ログのtail
docker logs -f ${PROJECT_NAME}-sample-mysql
```

## 動作確認

```bash
CONTAINER_NAME=${PROJECT_NAME}-sample-mysql

# rootユーザーでログイン
MYSQL_PWD=root1234 mysql -u root -h ${CONTAINER_NAME} -P 3306 sample

# appユーザーでログイン
MYSQL_PWD=pass1234 mysql -u app -h ${CONTAINER_NAME} -P 3306 sample
```



---



# ■ Redis

```bash
./bin/redis.sh

# ログのtail
docker logs -f ${PROJECT_NAME}-sample-redis
```

## 動作確認

### ログイン

```bash
CONTAINER_NAME=${PROJECT_NAME}-sample-redis
redis-cli -u redis://app:pass1234@${CONTAINER_NAME}:6379
```

### コマンド例

```bash
# 疎通確認
sample-redis:6379> PING
# PONG

# キーと値の設定・取得
sample-redis:6379> SET temp:room1 25.3
# OK
sample-redis:6379> GET temp:room1
# "25.3"

# インクリメント
sample-redis:6379> INCR cnt
# (integer) 1
sample-redis:6379> INCR cnt
# (integer) 2
sample-redis:6379> INCRBY cnt 3
# (integer) 5

# リスト操作
sample-redis:6379> LPUSH tasks "task1"
# (integer) 1
sample-redis:6379> LPUSH tasks "task2"
# (integer) 2
sample-redis:6379> LPUSH tasks "task3"
# (integer) 3
sample-redis:6379> LRANGE tasks 0 -1
# 1) "task3"
# 2) "task2"
# 3) "task1"

# 最後に追加した要素を取り出す
sample-redis:6379> LPOP tasks
# "task3"

# 最初に追加した要素を取り出す
sample-redis:6379> RPOP tasks
# "task1"

# 登録されているキーの一覧を表示
sample-redis:6379> KEYS *
# 1) "temp:room1"
# 2) "tasks"
# 3) "cnt"

# キーの削除
sample-redis:6379> DEL cnt

# Pub/Subチャンネル
sample-redis:6379> SUBSCRIBE temp:room1
# Reading messages... (press Ctrl-C to quit)
# 1) "subscribe"
# 2) "temp:room1"
# 3) (integer) 1
# 1) "message"
# 2) "temp:room1"
# 3) "25.5"
sample-redis:6379> PUBLISH temp:room1 "25.5"
# (integer) 1

```



---



# ■ RabbitMQ

```bash
./bin/rabbitmq.sh

# ログのtail
docker logs -f ${PROJECT_NAME}-sample-rabbitmq
```

## 動作確認

### 管理画面へのアクセス

- ポートフォワーディング 
  - `web-tutorial-v2-sample-rabbitmq:15672`
- 管理画面: http://localhost:15672
  - user: `app`
  - password: `pass1234`


### rabbitmqadminでの操作

```bash
CONTAINER_NAME=${PROJECT_NAME}-sample-rabbitmq
# キュー作成 (durable=true 永続化、再起動後も残る)
rabbitmqadmin \
  --host ${CONTAINER_NAME} \
  --port 15672 \
  --username app \
  --password pass1234 \
  declare queue --name myqueue --durable true

# メッセージ送信
rabbitmqadmin \
  --host ${CONTAINER_NAME} \
  --port 15672 \
  --username app \
  --password pass1234 \
  publish message --routing-key myqueue --payload "Hello, Rabbit!"

# メッセージ一覧
rabbitmqadmin \
  --host ${CONTAINER_NAME} \
  --port 15672 \
  --username app \
  --password pass1234 \
  list queues

# メッセージ取得 (--ack-mode ack_requeue_false 取得したメッセージをキューに戻さない。消費する)
rabbitmqadmin \
  --host ${CONTAINER_NAME} \
  --port 15672 \
  --username app \
  --password pass1234 \
  get messages --queue myqueue --ack-mode ack_requeue_false --count 1
```



---




# ■ Localstack

```bash
./bin/localstack.sh

# ログのtail
docker logs -f ${PROJECT_NAME}-sample-localstack
```

## 動作確認


```bash
export AWS_ENDPOINT_URL=http://${PROJECT_NAME}-sample-localstack:4566
export AWS_REGION=ap-northeast-1

# s3バケット
aws s3 ls
# 2025-11-08 14:10:30 sample

# snsトピック
aws sns list-topics
# {
#     "Topics": [
#         {
#             "TopicArn": "arn:aws:sns:ap-northeast-1:000000000000:sample-topic"
#         }
#     ]
# }

# SQS
aws sqs list-queues
# {
#     "QueueUrls": [
#         "http://sqs.ap-northeast-1.localhost.localstack.cloud:4566/000000000000/sample-sqs"
#     ]
# }


# DynamoDBテーブル一覧
aws dynamodb scan --table-name SensorReadings

# 指定したセンサーの一定期間のデータを取得
SENSOR_ID=sensor-001
ATTRIBUTE_VALUES=$(cat <<EOF
{
  ":p": {"S": "${SENSOR_ID}#$(date -u +"%Y%m%d")"},
  ":t1": {"S": "$(date -u +"%Y-%m-%dT00:00:00Z")"},
  ":t2": {"S": "$(date -u +"%Y-%m-%dT23:59:59Z")"}
}
EOF
)
aws dynamodb query \
  --table-name SensorReadings \
  --key-condition-expression "pk = :p AND ts BETWEEN :t1 AND :t2" \
  --expression-attribute-values "$ATTRIBUTE_VALUES"


# 指定したセンサーの最新データを取得
SENSOR_ID=sensor-002
ATTRIBUTE_VALUES=$(cat <<EOF
{":sid": {"S": "${SENSOR_ID}"}}
EOF
)
aws dynamodb query \
  --index-name GSI_SensorLatest \
  --table-name SensorReadings \
  --key-condition-expression "sensorId = :sid" \
  --expression-attribute-values "$ATTRIBUTE_VALUES" \
  --no-scan-index-forward \
  --limit 1

# 横浜エリアの全センサーで一定期間の30度以上のデータを取得
ATTRIBUTE_VALUES=$(cat <<EOF
{
  ":lb": {"S": "yokohama#$(date -u +"%Y%m%d")"},
  ":t1": {"S": "$(date -u +"%Y-%m-%dT00:00:00Z")"},
  ":t2": {"S": "$(date -u +"%Y-%m-%dT23:59:59Z")"},
  ":temp": {"N": "30"}
}
EOF
)
aws dynamodb query \
  --index-name GSI_LocationTime \
  --table-name SensorReadings \
  --key-condition-expression "locationBucket = :lb AND ts BETWEEN :t1 AND :t2" \
  --filter-expression "temperature >= :temp" \
  --expression-attribute-values "$ATTRIBUTE_VALUES"
```
