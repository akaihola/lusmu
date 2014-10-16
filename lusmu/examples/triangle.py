from lusmu.core import SrcNode, OpNode, update_source_nodes
from lusmu.visualization import visualize_graph
import math
import operator


a = SrcNode(name='length of cathetus a')
b = SrcNode(name='length of cathetus b')


def square(x):
    return x ** 2


def sum_(*args):
    return sum(args)


def sqrt(square):
    print '** taking square root of {:.2f}'.format(square)
    return math.sqrt(square)


area_a = OpNode(name='square of a',
                op=square,
                inputs=OpNode.inputs(a))
area_b = OpNode(name='square of b',
                op=square,
                inputs=OpNode.inputs(b))
area_hypothenuse = OpNode(name='square of hypothenuse',
                          op=sum_,
                          inputs=OpNode.inputs(area_a, area_b))
hypothenuse = OpNode(name='length of hypothenuse',
                     op=sqrt,
                     inputs=OpNode.inputs(area_hypothenuse))
sin_alpha = OpNode(name='sin of alpha',
                   op=operator.div,
                   inputs=OpNode.inputs(a, hypothenuse))
alpha = OpNode(name='angle alpha',
               op=math.asin,
               inputs=OpNode.inputs(sin_alpha))
sin_beta = OpNode(name='sin of beta',
                  op=operator.div,
                  inputs=OpNode.inputs(b, hypothenuse))
beta = OpNode(name='angle beta',
              op=math.asin,
              inputs=OpNode.inputs(sin_beta))


print 'Enter float values for a and b, e.g.\n> 3.0 4.0'
while True:
    answer = raw_input('\n> ')
    if not answer:
        break
    value_a, value_b = answer.split()
    update_source_nodes([(a, float(value_a)),
                         (b, float(value_b))])
    print 'Length of hypothenuse: {:.2f}'.format(hypothenuse.value)
    print 'Angle alpha: {:.2f} degrees'.format(math.degrees(alpha.value))
    print 'Angle beta: {:.2f} degrees'.format(math.degrees(beta.value))


try:
    visualize_graph([hypothenuse], 'triangle.png')
    print 'View triangle.png to see a visualization of the traph.'
except OSError:
    print 'Please install graphviz to visualize the graph.'
