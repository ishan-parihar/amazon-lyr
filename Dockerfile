FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY amazon_lyr ./amazon_lyr

RUN pip install --no-cache-dir .

# Cookies are mounted in, never baked: /config/amazon-lyr/cookies.json
VOLUME ["/root/.config/amazon-lyr"]

ENTRYPOINT ["amazon-lyr"]
CMD ["serve"]
