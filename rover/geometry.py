"""Physical footprint operations in board millimetres."""
import math

def corners(pose, footprint):
    c,s=math.cos(pose.heading_rad),math.sin(pose.heading_rad)
    a,b=footprint['length_mm']/2,footprint['width_mm']/2
    return [(pose.x_mm+c*x-s*y,pose.y_mm+s*x+c*y) for x,y in ((a,b),(a,-b),(-a,b),(-a,-b))]

def edge_clearance_mm(pose, footprint, board_size):
    return min(min(x,y,board_size['width_mm']-x,board_size['height_mm']-y) for x,y in corners(pose,footprint))

def footprints_overlap(pose, length_mm, width_mm, player):
    dx,dy=player['x_mm']-pose.x_mm,player['y_mm']-pose.y_mm
    c,s=math.cos(pose.heading_rad),math.sin(pose.heading_rad)
    x,y=c*dx+s*dy,-s*dx+c*dy
    dx=max(abs(x)-length_mm/2,0);dy=max(abs(y)-width_mm/2,0)
    return dx*dx+dy*dy<=player['radius_mm']**2+1e-9
