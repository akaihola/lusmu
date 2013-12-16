from lusmu.core import Input, Node, update_inputs
from lusmu.visualization import visualize_graph
import math
import operator


a = Input(name='length of cathetus a')
b = Input(name='length of cathetus b')


def square(x):
    return x ** 2


def sum_(*args):
    return sum(args)


def sqrt(square):
    print '** taking square root of {:.2f}'.format(square)
    return math.sqrt(square)


area_a = Node(name='square of a',
              action=square,
              inputs=Node.inputs(a))
area_b = Node(name='square of b',
              action=square,
              inputs=Node.inputs(b))
area_hypothenuse = Node(name='square of hypothenuse',
                        action=sum_,
                        inputs=Node.inputs(area_a, area_b))
hypothenuse = Node(name='length of hypothenuse',
                   action=sqrt,
                   inputs=Node.inputs(area_hypothenuse))
sin_alpha = Node(name='sin of alpha',
                 action=operator.div,
                 inputs=Node.inputs(a, hypothenuse))
alpha = Node(name='angle alpha',
             action=math.asin,
             inputs=Node.inputs(sin_alpha))
sin_beta = Node(name='sin of beta',
                action=operator.div,
                inputs=Node.inputs(b, hypothenuse))
beta = Node(name='angle beta',
            action=math.asin,
            inputs=Node.inputs(sin_beta))


print 'Enter float values for a and b, e.g.\n> 3.0 4.0'
while True:
    answer = raw_input('\n> ')
    if not answer:
        break
    value_a, value_b = answer.split()
    update_inputs([(a, float(value_a)),
                   (b, float(value_b))])
    print 'Length of hypothenuse: {:.2f}'.format(hypothenuse.value)
    print 'Angle alpha: {:.2f} degrees'.format(math.degrees(alpha.value))
    print 'Angle beta: {:.2f} degrees'.format(math.degrees(beta.value))


try:
    visualize_graph([hypothenuse], 'triangle.png')
    print 'View triangle.png to see a visualization of the traph.'
except OSError:
    print 'Please install graphviz to visualize the graph.'
