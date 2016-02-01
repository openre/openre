{% block pragma %}
#pragma OPENCL EXTENSION cl_khr_global_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_global_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_local_int32_extended_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable
#pragma OPENCL EXTENSION cl_khr_int64_base_atomics : enable
{% endblock %}

{% block types %}
/* neuron.flags */
{{ types.neuron_flags | to_c_type }} constant IS_INHIBITORY = 1<<0;
{{ types.neuron_flags | to_c_type }} constant IS_SPIKED = 1<<1;
{{ types.neuron_flags | to_c_type }} constant IS_DEAD = 1<<2;
{{ types.neuron_flags | to_c_type }} constant IS_TRANSMITTER = 1<<3;
{{ types.neuron_flags | to_c_type }} constant IS_RECEIVER = 1<<4;
/* synapse.flags */
{{ types.synapse_flags | to_c_type }} constant IS_STRENGTHENED = 1<<0;
/* openre.data_types.null */
{{ types.address | to_c_type }} constant NULL_ADDRESS = {{ null }};
{% endblock %}

{% block code %}
{% endblock %}


