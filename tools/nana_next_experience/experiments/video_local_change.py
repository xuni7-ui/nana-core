"""Experimental local pixel-change region; not text or semantic detection."""
from statistics import median


def local_change(before, after, *, threshold=24, min_pixels=6, max_fraction=0.15, padding=4):
    """Find a bounded small change after compensating a global luminance shift.

    Inputs are same-sized PIL images in source pixel coordinates. Return a
    proposed box, or None for sparse noise, large changes, or no local change.
    A proposal can be cursor motion, compression noise, or any other change;
    it is not evidence that text exists or that a model should inspect it.
    """
    width,height=before.size
    if (after.size != before.size or width < 1 or height < 1 or width*height > 262144
            or type(threshold) is not int or not 1 <= threshold <= 255
            or type(min_pixels) is not int or min_pixels < 1
            or not 0 < max_fraction <= 1 or type(padding) is not int or not 0 <= padding <= 64):
        raise ValueError('invalid image or proposal bounds')
    a=before.convert('L').tobytes();b=after.convert('L').tobytes()
    shifts=[v-u for u,v in zip(a,b)]
    global_shift=median(shifts)
    points=[i for i,shift in enumerate(shifts) if abs(shift-global_shift)>=threshold]
    if len(points)<min_pixels or len(points)>len(shifts)*max_fraction:
        return None
    xs=[i%width for i in points];ys=[i//width for i in points]
    left=max(0,min(xs)-padding);top=max(0,min(ys)-padding)
    right=min(width,max(xs)+1+padding);bottom=min(height,max(ys)+1+padding)
    # Dispersed tiny changes across the frame should not create a huge crop.
    if (right-left)*(bottom-top)>width*height*max_fraction:
        return None
    return {'box':(left,top,right,bottom),'changed_pixels':len(points),
            'global_luminance_shift':global_shift,'coordinate_space':'input_pixels',
            'meaning':'local visual change only; no text or semantic classification'}


def crop_local_change(image, proposal, *, scale=2):
    """Crop from the original image and optionally enlarge, retaining location.

    This is an in-memory image helper. The caller remains responsible for the
    frame's source, timestamp, identity, privacy, and any later storage.
    """
    from PIL import Image
    if (not isinstance(proposal,dict) or proposal.get('coordinate_space')!='input_pixels'
            or type(scale) is not int or not 1<=scale<=4):
        raise ValueError('invalid crop proposal')
    box=proposal.get('box')
    if (not isinstance(box,tuple) or len(box)!=4 or any(type(v) is not int for v in box)):
        raise ValueError('invalid crop coordinates')
    left,top,right,bottom=box;width,height=image.size
    if (not 0<=left<right<=width or not 0<=top<bottom<=height or
            (right-left)*scale>1024 or (bottom-top)*scale>1024):
        raise ValueError('crop outside bounds')
    cropped=image.crop(box)
    if scale>1:
        cropped=cropped.resize((cropped.width*scale,cropped.height*scale),Image.Resampling.LANCZOS)
    return cropped,{'source_box':box,'coordinate_space':'input_pixels','scale':scale}
