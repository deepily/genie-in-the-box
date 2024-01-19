def print_device_allocation( model ):

    for name, param in model.named_parameters():
       print( f"{name}: {param.device}" )

def is_allocated_to_cpu( model ):

    # test to see if *any* parameter is stashed on the cpu
    for name, param in model.named_parameters():
        if param.device.type == "cpu": return True

    return False
