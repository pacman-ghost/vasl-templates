cd `dirname "$0"`/proto

# initialize
rm -rf generated 2>/dev/null
mkdir generated

# compile the protobuf definitions
python -m grpc_tools.protoc \
    --proto_path . \
    --python_out=generated/ \
    --grpc_python_out=generated/ \
    control_tests.proto

# FUDGE! Fix a bogus import :-/
sed --in-place \
    's/^import control_tests_pb2 as control__tests__pb2$/import vasl_templates.webapp.tests.proto.generated.control_tests_pb2 as control__tests__pb2/' \
    generated/control_tests_pb2_grpc.py
