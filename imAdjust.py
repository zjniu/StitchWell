from numba import jit

@jit
def imAdjust(I,low_in,high_in,low_out,high_out,gamma=1):
    
    # Similar to imadjust in MATLAB.
    # Converts an image range from [low_in,high_in] to [low_out,high_out].
    # The Equation of a line can be used for this transformation:
    #   y=((high_out-low_out)/(high_in-low_in))*(I-low_in)+low_out
    # However, it is better to use a more generalized equation:
    #   y=((I-low_in)/(high_in-low_in))^gamma*(high_out-low_out)+low_out
    # If gamma is equal to 1, then the line equation is used.
    # When gamma is not equal to 1, then the transformation is not linear.

    return (((I - low_in) / (high_in - low_in)) ** gamma) * (high_out - low_out) + low_out