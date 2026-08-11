FROM debian:stable-slim

RUN apt-get update && \
    apt-get install -y nginx tcpdump iproute2 iputils-ping curl && \
    rm -rf /var/lib/apt/lists/*

# Remove the default Nginx config and copy our custom one
RUN rm -f /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Create dummy static assets to satisfy sub-resource fetch behaviour
RUN mkdir -p /var/www/html/static /var/www/html/img
RUN echo "body { background: #f4f4f4; }" > /var/www/html/static/app.css
RUN echo "console.log('App loaded successfully');" > /var/www/html/static/app.js
RUN echo "fake_image_payload" > /var/www/html/img/product_1.jpg

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]