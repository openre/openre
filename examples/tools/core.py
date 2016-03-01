# Pretty print OpenCL program
from openre.data_types import types, null
from openre.templates import create_env


env = create_env()
source_file_name = "device/opencl.c"
code = env.get_template(source_file_name).render(
    types=types,
    null=null
)
print code
