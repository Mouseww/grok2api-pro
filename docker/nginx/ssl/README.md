# SSL 证书目录

将您的SSL证书放置在此目录：

- `fullchain.pem` - 完整证书链
- `privkey.pem` - 私钥文件

## 获取证书

### Let's Encrypt (免费)

```bash
# 安装 certbot
apt-get install certbot

# 获取证书
certbot certonly --standalone -d your-domain.com

# 证书位置
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

### 自签名证书 (仅测试)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout privkey.pem \
    -out fullchain.pem \
    -subj "/CN=localhost"
```

## 注意事项

- 证书文件不应提交到版本控制
- 生产环境请使用正规CA签发的证书
- 定期更新Let's Encrypt证书（有效期90天）
