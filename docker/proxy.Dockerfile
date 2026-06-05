FROM nginx:1.31-alpine
# / -> frontend, /api/ -> backend に振り分ける設定（開発用と同じ default.conf）
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf