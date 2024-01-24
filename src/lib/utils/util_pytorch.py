import gc
import torch

def print_device_allocation( model ):

    for name, param in model.named_parameters():
       print( f"{name}: {param.device}" )

def is_allocated_to_cpu( model ):

    # test to see if *any* parameter is stashed on the cpu
    for name, param in model.named_parameters():
        if param.device.type == "cpu": return True

    return False

def release_gpu_memory( model ):
    
    # See: https://www.phind.com/search?cache=kh81ys0uelwxs8zpykdzv0d8
    
    model.device = torch.device( "cpu" )
    model        = None
    
    gc.collect()
    torch.cuda.empty_cache()