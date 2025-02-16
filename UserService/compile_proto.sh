#!/bin/bash

# Directory where the .proto files are located
PROTO_SRC="grpc_api/protobuf"

# Directory where the generated Python files will be saved
OUT_DIR="grpc_api/messages"

# Compile the .proto files using the protoc compiler with gRPC and Python plugins
python -m grpc_tools.protoc -I$PROTO_SRC --python_out=$OUT_DIR --grpc_python_out=$OUT_DIR $PROTO_SRC/*.proto

# Check if the compilation was successful
if [ $? -eq 0 ]; then
    echo "Compilation successful!"
else
    echo "Compilation failed!"
    exit 1
fi