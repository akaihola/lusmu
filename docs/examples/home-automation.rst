Home automation example
=======================

This is an example of using reactive programming and the Lusmu library
in a home automation setting.

First, import the Lusmu :class:`~lusmu.core.Input`
and :class:`~lusmu.core.OpNode` classes,
the :func:`~lusmu.core.update_inputs` function for inserting input values
and the Python :mod:`math` package::

    from lusmu.core import Input, OpNode, update_inputs
    import math

Them define the action functions
to be used in the home automation system.

.. note:: Actions with positional arguments
          receive them as separate arguments, not as a list.
          This is why we need to wrap Python's :func:`sum` function.

::

    def avg(*args):
        return sum(args) / len(args)

    def sum_(*args):
        return sum(args)

    def inverse(max_value):
        def _inverse(value):
            return max_value - value
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

    temperature_1 = Input()
    temperature_2 = Input()
    temperature_avg = OpNode(action=avg,
                             inputs=OpNode.inputs(temperature_1, temperature_2))
    temperature_threshold = OpNode(action=lambda temperature: temperature > 20.0,
                                   inputs=OpNode.inputs(temperature_avg))

    def switch_heater(should_be_off):
        print 'Heater {}'.format('off' if should_be_off else 'on')

    heater = OpNode(action=switch_heater,
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

    brightness_1 = Input()
    brightness_2 = Input()
    brightness_sum = OpNode(action=sum_,
                            inputs=OpNode.inputs(brightness_1, brightness_2))
    brightness_inverse = OpNode(action=inverse(510),
                                inputs=OpNode.inputs(brightness_sum))

    def set_lamp_power(power):
        print 'Lamp power {:.2f}'.format(power)

    lamp_power = OpNode(action=set_lamp_power,
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

    humidity = Input()
    humidity_normalized = OpNode(action=lambda sensor_value: 100.0 * (1.0 - math.log(sensor_value, 255)),
                                 inputs=OpNode.inputs(humidity))

Initially the value of all nodes is undefined.
The :obj:`lusmu.core.DIRTY` special object is used
to denote an undefined value.
The private :attr:`~lusmu.core.OpNode._value` attribute
can be inspected to see the cached value of the node
without triggering lazy evaluation::

    >>> temperature_avg._value
    <lusmu.core.DIRTY>

Values are fed into input nodes
using the :func:`~lusmu.core.update_inputs` function::

    >>> update_inputs([(temperature_1, 25.0),
    ...                (temperature_2, 22.5),
    ...                (brightness_1, 100),
    ...                (brightness_2, 110),
    ...                (humidity, 50)])
    Heater off
    Lamp power 300.0

Since the heater and lamp control nodes
are defined as auto-calculated (``triggered=True``),
all nodes on those dependency paths are evaluated
when values of nodes are updated::

    >>> temperature_avg._value
    23.75
    >>> brightness_sum._value
    210

On the other hand, the relative humidity value is not auto-calculated::

    >>> humidity_normalized._value
    <lusmu.core.DIRTY>

The dependency path from the input node to the requested humidity value
is only evaluated when needed.
The :attr:`lusmu.core.OpNode.value` property triggers evaluation::

    >>> humidity_normalized.value
    29.40196809721851

Unchanged values don't trigger evaluation:

    >>> update_inputs([(temperature_1, 25.0),
    ...                (temperature_2, 22.5)})

Changing the values does::

    >>> update_inputs([(temperature_1, 21.0),
    ...                (temperature_2, 18.5)])
    Heater on
    Lamp power 405.00
