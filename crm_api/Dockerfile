FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m grpc_tools.protoc -I./protos --python_out=./protos --grpc_python_out=./protos ./protos/dealership.proto
RUN sed -i 's/import dealership_pb2 as dealership__pb2/from . import dealership_pb2 as dealership__pb2/g' protos/dealership_pb2_grpc.py
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8080"]