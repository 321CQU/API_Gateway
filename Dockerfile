FROM python:3.11

ENV TZ=Asia/Shanghai
ENV PATH="/src/.venv/bin:$PATH"

WORKDIR /src
COPY pyproject.toml uv.lock /src/
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple uv \
    && uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000

CMD ["python", "server.py"]