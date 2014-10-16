Home automation example
=======================

This is an example of using reactive programming and the Lusmu library
in a home automation setting.

First, import the Lusmu :class:`~lusmu.core.SrcNode`
and :class:`~lusmu.core.OpNode` classes,
the :func:`~lusmu.core.update_source_nodes` function for inserting input values
and the Python :mod:`math` package::

    from lusmu.core import SrcNode, OpNode, update_source_nodes
    import math

Then define the operation functions
to be used in the home automation system.

.. note:: Operations with positional arguments
          receive them as separate arguments, not as a list.
          This is why we need to wrap Python's :func:`sum` function.

::

    def avg(*args):
        return sum(args) / len(args)

    def sum_(*args):
        return sum(args)

    def inverse(max_value):
        def _inverse(data):
            return max_value - data
        return _inverse

The output from two temperature sensors are averaged,
and a lower limit of 20.0 degrees is used to switch the heater off:

.. graphviz::

   digraph temperature {
      temperature_1 [shape=diamond];
      temperature_2 [shape=diamond];
      temperature_1 -> temperature_avg;
      temperature_2 -> temperature_avg;
      temperature_avg -> temperature_threshold;
      temperature_threshold -> heater;
   }

::

    temperature_1 = SrcNode()
    temperature_2 = SrcNode()
    temperature_avg = OpNode(op=avg,
                             inputs=OpNode.inputs(temperature_1, temperature_2))
    temperature_threshold = OpNode(op=lambda temperature: temperature > 20.0,
                                   inputs=OpNode.inputs(temperature_avg))

    def switch_heater(should_be_off):
        print 'Heater {}'.format('off' if should_be_off else 'on')

    heater = OpNode(op=switch_heater,
                    inputs=OpNode.inputs(temperature_threshold),
                    triggered=True)

The lights are adjusted according to brightness sensors in the windows:

.. graphviz::

   digraph brightness {
      brightness_1 [shape=diamond];
      brightness_2 [shape=diamond];
      brightness_1 -> brightness_sum;
      brightness_2 -> brightness_sum;
      brightness_sum -> brightness_inverse;
      brightness_inverse -> lamp_power;
   }

::

    brightness_1 = SrcNode()
    brightness_2 = SrcNode()
    brightness_sum = OpNode(op=sum_,
                            inputs=OpNode.inputs(brightness_1, brightness_2))
    brightness_inverse = OpNode(op=inverse(510),
                                inputs=OpNode.inputs(brightness_sum))

    def set_lamp_power(power):
        print 'Lamp power {:.2f}'.format(power)

    lamp_power = OpNode(op=set_lamp_power,
                        inputs=OpNode.inputs(brightness_inverse),
                        triggered=True)

Based on output of the humidity sensor,
the relative humidity is calculated:

.. graphviz::

   digraph humidity {
      humidity [shape=diamond];
      humidity -> humidity_normalized;
   }
 
::

    humidity = SrcNode()
    humidity_normalized = OpNode(op=lambda sensor_value: 100.0 * (1.0 - math.log(sensor_value, 255)),
                                 inputs=OpNode.inputs(humidity))

Initially the data of all nodes is undefined.
The :obj:`lusmu.core.NO_DATA` special object is used
to denote undefined data.
The private :attr:`~lusmu.core.OpNode._data` attribute
can be inspected to see the cached data of the node
without triggering lazy evaluation::

    >>> temperature_avg._data
    <lusmu.core.NO_DATA>

Data is fed into source nodes
using the :func:`~lusmu.core.update_source_nodes` function::

    >>> update_source_nodes([(temperature_1, 25.0),
    ...                      (temperature_2, 22.5),
    ...                      (brightness_1, 100),
    ...                      (brightness_2, 110),
    ...                      (humidity, 50)])
    Heater off
    Lamp power 300.0

Since the heater and lamp control nodes
are defined as auto-calculated (``triggered=True``),
all nodes on those dependency paths are evaluated
when data of nodes are updated::

    >>> temperature_avg._data
    23.75
    >>> brightness_sum._data
    210

On the other hand, the relative humidity value is not auto-calculated::

    >>> humidity_normalized._data
    <lusmu.core.NO_DATA>

The dependency path from the source node to the requested humidity value
is only evaluated when needed.
The :attr:`lusmu.core.OpNode.data` property triggers evaluation::

    >>> humidity_normalized.data
    29.40196809721851

Unchanged data doesn't trigger evaluation:

    >>> update_source_nodes([(temperature_1, 25.0),
    ...                      (temperature_2, 22.5)})

Changing data does::

    >>> update_source_nodes([(temperature_1, 21.0),
    ...                      (temperature_2, 18.5)])
    Heater on
    Lamp power 405.00
