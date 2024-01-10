def print_device_allocation( model ):

    for name, param in model.named_parameters():
       print( f"{name}: {param.device}" )
