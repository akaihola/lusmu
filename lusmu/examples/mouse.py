"""An interactive mouse-based example

This script tracks whether mouse clicks hit a circle.

On the screen there's a circle with a fixed center and radius.  Mouse clicks
inside and outside the circle to change its color.

On click (and drag), mouse coordinates are fed into the ``mousex`` and
``mousey`` source nodes.  The ``distance`` operation node takes those
coordinates as inputs, and outputs the distance to the center of the circle.
The result is fed into the ``is_close`` operation node, which outputs a
``True`` value for distances smaller than the circle radius.  The ``alert``
operation node returns a string whose value depends on that boolean value.
Finally, the circle changes its color based on the string in the ``alert``
node.

You can also observe debug output on the console.  Note how the distance
measurement is skipped if the coordinate inputs don't change.

If you have the graphviz tool installed, you'll also see a diagram of the graph
nodes and connections on the screen.  The diagram is saved in ``mouse.gif``.

"""


from lusmu.core import SrcNode, OpNode, update_source_nodes
from lusmu.visualization import visualize_graph
import math
import Tkinter


TARGET = {'x': 90, 'y': 110}
RADIUS = 30


def get_distance(x, y):
    print ('Measuring distance from ({x}, {y}) to {t[x]}'
           .format(x=x, y=y, t=TARGET))
    dx = x - TARGET['x']
    dy = y - TARGET['y']
    return math.sqrt(dx ** 2 + dy ** 2)


def is_close_to_target(distance):
    return distance < RADIUS


def get_distance_description(is_close):
    return "INSIDE" if is_close else "OUTSIDE"


mousex = SrcNode(name='mouse x')
mousey = SrcNode(name='mouse y')
distance = OpNode(
    name='distance',
    op=get_distance,
    inputs=OpNode.inputs(mousex, mousey))
is_close = OpNode(
    name='is close',
    op=is_close_to_target,
    inputs=OpNode.inputs(distance))
alert = OpNode(
    name='alert',
    op=get_distance_description,
    inputs=OpNode.inputs(is_close))


def onclick(event):
    update_source_nodes([(mousex, event.x),
                         (mousey, event.y)])
    print 'distance.data == {:.1f}'.format(distance.data)
    print 'is_close.data == {!r}'.format(is_close.data)
    print 'alert.data == {!r}'.format(alert.data)
    print
    colors = {'INSIDE': 'red', 'OUTSIDE': 'blue'}
    draw_circle(colors[alert.data])


def draw_circle(color):
    tx = TARGET['x']
    ty = TARGET['y']
    canvas.create_oval(tx - RADIUS, ty - RADIUS, tx + RADIUS, ty + RADIUS,
                       fill=color)


root = Tkinter.Tk()
frame = Tkinter.Frame(root)
frame.pack(fill=Tkinter.BOTH, expand=1)
canvas = Tkinter.Canvas(frame, background='white')
draw_circle('blue')
canvas.pack(fill=Tkinter.BOTH, expand=1)
canvas.pack()
canvas.bind("<Button-1>", onclick)
canvas.bind("<B1-Motion>", onclick)

try:
    visualize_graph([alert], 'mouse.gif')
    print 'View mouse.gif to see a visualization of the traph.'
    diagram = Tkinter.PhotoImage(file='mouse.gif')
    canvas.create_image(0, 2 * (TARGET['y'] + RADIUS),
                        image=diagram, anchor='nw')
except OSError:
    print 'Please install graphviz to visualize the graph.'

root.mainloop()
