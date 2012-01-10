#!/usr/bin/env python2
""" The Eagle Format Parser """

# upconvert.py - A universal hardware design file format converter using
# Format:       upverter.com/resources/open-json-format/
# Development:  github.com/upverter/schematic-file-converter
#
# Copyright 2011 Upverter, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Note: It parses a file of an Eagle format of version up to 5.11.
# Default values are used for fields missed in files of previous versions.
#

import struct

from core.design import Design

class EagleBinConsts:
    """ Just a set of constants to be used by both parser and writer
    """
    pass

class Eagle:
    """ The Eagle Format Parser """

    
    class Header:
        """ A struct that represents a header """
        constant = 0x10
        template = "=4BI4B3I"

        def __init__(self, version="5.11", numofblocks=0):
            """ Just a constructor
            """
            self.version = version # has to be of x.y (dot-separated) format
            self.numofblocks = numofblocks
            return

        @staticmethod
        def parse(chunk):
            """ Parses header block
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Header.template, chunk)

            _ret_val = Eagle.Header(
                                version='%s.%s' % (str(_dta[5]),str(_dta[6])),
                                numofblocks=_dta[4], # including this one
                                      )
# [13] -- some number / counter ; changed on each 'save as' (even with no changes)
            return _ret_val

    class Settings:
        """ A struct that represents ?? settings ??
        """
        constant = 0x11
        template = "=4BI4BII4B"

        # TODO if i need to synchronize access?..
        counter = 0

        def __init__(self, copyno=0, seqno=None):
            """ Just a constructor
            """
            if None == seqno:
                seqno = Eagle.Settings.counter
                Eagle.Settings.counter += 1
            else:
                Eagle.Settings.counter = 1 + seqno
            self.seqno = seqno # looks like first and second blocks
                               #  starts with the same byte set
                               #  but then the second set starts to evolve
            self.copyno = copyno # holds No of a 'Save As..' copy
            return

        @staticmethod
        def parse(chunk):
            """ Parses ?? settings ?? block
                TODO synchronization could be needed
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Settings.template, chunk)

# [11] -- sequence number of a copy (incremented on each 'save as', even with no changes)
#          (for first "settings" block only; second one contains 0 there)
            _ret_val = Eagle.Settings(seqno=Eagle.Settings.counter,
                                         copyno=_dta[8]
                                        )
            Eagle.Settings.counter += 1
            return _ret_val

    class Grid:
        """ A struct that represents a grid
        """
        constant = 0x12
        template = "=4B5I"

        unitmask = 0x0f
        units = {
                 0x0f: "inch",
                 0x00: "mic",
                 0x05: "mm",
                 0x0a: "mil",
                }
        lookmask = 2
        look = {
                0: "lines",
                2: "dots",
               }
        showmask = 1
        show = {
                0: False,
                1: True,
               }

        def __init__(self, distance=0.1, unitdist="inch", unit="inch", 
                style="lines", multiple=1, display=False, altdistance=0.01, 
                altunitdist="inch", altunit="inch"):
            """ Just a constructor
            """
            self.distance = distance
            self.unitdist = unitdist
            self.unit = unit
            self.style = style
            self.multiple = multiple
            self.display = display
            self.altdistance = altdistance
            self.altunitdist = altunitdist
            self.altunit = altunit
            return

        @staticmethod
        def parse(chunk):
            """ Parses grid block
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Grid.template, chunk)

            try:
                _unit = Eagle.Grid.units[Eagle.Grid.unitmask & _dta[3]]
            except KeyError: # unknown grid measure units
                _unit = "n/a"

            try:
                _altunit = Eagle.Grid.units[Eagle.Grid.unitmask & 
                                               (_dta[3] >> 4)]
            except KeyError: # unknown grid alt measure units
                _altunit = "n/a"

# strage float format here: 8 bytes ; no idea yet
# thus proceeding in 6.0.0 way: default values are used
# (but units are preserved; 6.0.0 uses default set -- with inches)
            _ret_val = Eagle.Grid(
                                     distance=0.1, # <--- here [7:15]
                                     unitdist=_unit,
                                     unit=_unit,
                                     style=Eagle.Grid.look[
                                            Eagle.Grid.lookmask & _dta[2]],
                                     multiple=_dta[4],
                                     display=Eagle.Grid.show[
                                            Eagle.Grid.showmask & _dta[2]],
                                     altdistance=0.01, # <--- here [15:23]
                                     altunitdist=_altunit,
                                     altunit=_altunit
                                    )
            return _ret_val

    class Layer:
        """ A struct that represents a layer
        """
        constant = 0x13
        template = "=7B2I9s"

#        colors = ['unknown','darkblue','darkgreen','darkcyan',
#                'darkred','unknown','khaki','grey',
## light variants x8
#                 ]
#        fill = ['none','filled',
## total 16; different line and dot patterns
#               ]

        def __init__(self, number, name, color, fill, visible, active):
            """ Just a constructor
            """
            self.number = number
            self.name = name
            self.color = color
            self.fill = fill
            self.visible = visible
            self.active = active
            return

        @staticmethod
        def parse(chunk):
            """ Parses single layer block
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Layer.template, chunk)

# these visible / active signs looks like legacy ones
#  and older format files have other values for this octet
            _visible = False
            _active = False
            if 0x03 == _dta[2]:
                _visible = False
                _active = True
            elif 0x0f == _dta[2]:
                _visible = True
                _active = True
            else:
                pass # unknown layer visibility sign

            _ret_val = Eagle.Layer(number=_dta[3], # or [4], they're the same
                                      name=_dta[9],
                                      color=_dta[6],
                                      fill=_dta[5], 
                                      visible=_visible,
                                      active=_active
                                     )
            return _ret_val

    class AttributeHeader:
        """ A struct that represents a header of attributes
        """
        constant = 0x14
        template = "=4BIII4BI"

        def __init__(self, numofshapes=0, numofattributes=0):
            """ Just a constructor
            """
            self.numofshapes = numofshapes # to be validated!
            self.numofattributes = numofattributes # to be validated!
            return

        @staticmethod
        def parse(chunk):
            """ Parses attribute header block
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.AttributeHeader.template, chunk)

# number of shapes + header of shapes
# number of attributes, excluding this line
# [19] -- a kind of a marker, 0x7f
# TODO decode [20:24], looks like int changed on each 'save as', even with no changes
            _ret_val = Eagle.AttributeHeader(numofshapes=(-1 + _dta[5]),
                                                numofattributes=_dta[6]
                                               )
            return _ret_val

    class ShapeHeader:
        """ A struct that represents a header of shapes
        """
        constant = 0x1a
        template = "=2BH5I"

        def __init__(self, numofshapes=0):
            """ Just a constructor
            """
            self.numofshapes = numofshapes # to be validated!
            return

        @staticmethod
        def parse(chunk):
            """ Parses shape header block
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.ShapeHeader.template, chunk)

# number of shapes, excluding this header block
            _ret_val = Eagle.ShapeHeader(numofshapes=_dta[2],
                                           )
            return _ret_val

    class Shape(object):
        """ A base struct for shapes, provides common codecs
             Although it provides two scaling methods, #2 has 
             to be used all the time
        """

        scale1a = 1000000.0
        scale1b = 2
        scale2 = 10000.0

        width_xscale = 2
        size_xscale = 2
        ratio_sscale = 2

        rotatemask = 0x0f
        rotates = {
                   0x00: None,
                   0x04: "R90",
                   0x08: "R180",
                   0x0c: "R270",
                  }

        fonts = {
                  0x00: "vector",
                  0x01: None, # "proportional",
                  0x02: "fixed",
                 }

        def __init__(self, layer):
            """ Just a constructor
            """
            self.layer = layer
            return 

        @staticmethod
        def decode_real(number, algo=2):
            """ Transforms given binary array to a float
            """
            _ret_val = 0
            if 1 == algo:
                _ret_val = ((number << Eagle.Shape.scale1b) / 
                                                Eagle.Shape.scale1a)
            elif 2 == algo:
                _ret_val = number / Eagle.Shape.scale2
            return _ret_val

    class Circle(Shape):
        """ A struct that represents a circle
        """
        constant = 0x25
        template = "=4B4IH2B"

        def __init__(self, x, y, radius, width, layer):
            """ Just a constructor
            """
            super(Eagle.Circle, self).__init__(layer)
            self.x = x
            self.y = y
            self.radius = radius
            self.width = width
            return

        @staticmethod
        def parse(chunk):
            """ Parses rectangle
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Circle.template, chunk)

            _ret_val = Eagle.Circle(
                                      x=Eagle.Shape.decode_real(_dta[4]),
                                      y=Eagle.Shape.decode_real(_dta[5]),
                                      radius=Eagle.Shape.decode_real(_dta[6]), # the same as [7]
                                      layer=_dta[3],
                                      width=(Eagle.Circle.width_xscale *
                                             Eagle.Shape.decode_real(
                                                                    _dta[8]))
                                         )
            return _ret_val

    class Rectangle(Shape):
        """ A struct that represents a rectangle
        """
        constant = 0x26
        template = "=4B4I4B"

        def __init__(self, x1, y1, x2, y2, layer, rotate):
            """ Just a constructor
            """
            super(Eagle.Rectangle, self).__init__(layer)
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
            self.rotate = rotate
            return

        @staticmethod
        def parse(chunk):
            """ Parses rectangle
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Rectangle.template, chunk)

            _ret_val = Eagle.Rectangle(
                                      x1=Eagle.Shape.decode_real(_dta[4]),
                                      y1=Eagle.Shape.decode_real(_dta[5]),
                                      x2=Eagle.Shape.decode_real(_dta[6]),
                                      y2=Eagle.Shape.decode_real(_dta[7]),
                                      layer=_dta[3],
                                      rotate=Eagle.Rectangle.rotates[_dta[9]]
                                         )
            return _ret_val

    class Web(object):
        """ A base struct for a bunch of segments
            It's needed to uniform parsing and counting of members
        """

        def __init__(self, name, numofblocks=0, segments=None):
            """ Just a constructor
            """
            self.name = name
            if None == segments:
                segments = []
            self.segments = segments
            self.numofblocks = numofblocks
            return

    class Net(Web):
        """ A struct that represents a net
        """
        constant = 0x1f
        template = "=2BH3I8s"

        constantmid1 = 0x7fff7fff
        constantmid2 = 0x80008000

        def __init__(self, name, nclass, numofblocks=0, segments=None):
            """ Just a constructor
            """
            super(Eagle.Net, self).__init__(name, numofblocks, segments)
            self.nclass = nclass
            return

        @staticmethod
        def parse(chunk):
            """ Parses net
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Net.template, chunk)

            if (Eagle.Net.constantmid1 != _dta[3] or 
                    Eagle.Net.constantmid2 != _dta[4]):
                logging.error("strange mid-constants in net " + _dta[6])

            _ret_val = Eagle.Net(name=_dta[6],
                                    nclass=_dta[5],
                                    numofblocks=_dta[2],
                                   )
            return _ret_val

    class Segment:
        """ A struct that represents a segment
        """
        constant = 0x20
        template = "=2BHI4B3I"

        def __init__(self, numofshapes=0, wires=None, junctions=None,
                     labels=None, cumulativenumofshapes=0):
            """ Just a constructor
            """
            self.cumulativenumofshapes = cumulativenumofshapes
            self.numofshapes = numofshapes
            if None == wires:
                wires = []
            self.wires = wires
            if None == junctions:
                junctions = []
            self.junctions = junctions
            if None == labels:
                labels = []
            self.labels = labels
            return

        @staticmethod
        def parse(chunk):
            """ Parses segment
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Segment.template, chunk)

            _ret_val = Eagle.Segment(numofshapes=_dta[2],
                                        cumulativenumofshapes=_dta[5],
                                       )
            return _ret_val

    class Wire(Shape):
        """ A struct that represents a wire
        """
        constant = 0x22
        template = "=4B4iH2B"

        arc_sign = 0x81

        def __init__(self, x1, y1, x2, y2, layer, width):
            """ Just a constructor
            """
            super(Eagle.Wire, self).__init__(layer)
            self.x1 = x1
            self.y1 = y1
            self.x2 = x2
            self.y2 = y2
            self.width = width
            return

        @staticmethod
        def parse(chunk):
            """ Parses wire
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Wire.template, chunk)

            if Eagle.Wire.arc_sign != _dta[10]:
                _ret_val = Eagle.Wire(
                                      x1=Eagle.Shape.decode_real(_dta[4]),
                                      y1=Eagle.Shape.decode_real(_dta[5]),
                                      x2=Eagle.Shape.decode_real(_dta[6]),
                                      y2=Eagle.Shape.decode_real(_dta[7]),
                                      layer=_dta[3],
                                      width=(Eagle.Wire.width_xscale *
                                             Eagle.Shape.decode_real(
                                                                    _dta[8]))
                                         )
            else: # Arc features "packed" coordinates...
                _ret_val = Eagle.Arc.parse(chunk)

            return _ret_val

    class Junction(Shape):
        """ A struct that represents a junction
        """
        constant = 0x27
        template = "=4B5I"

        constantmid = 0x000013d8

        def __init__(self, x, y, layer):
            """ Just a constructor
            """
            super(Eagle.Junction, self).__init__(layer)
            self.x = x
            self.y = y
            return

        @staticmethod
        def parse(chunk):
            """ Parses junction
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Junction.template, chunk)

            _ret_val = Eagle.Junction(x=Eagle.Shape.decode_real(_dta[4]),
                                         y=Eagle.Shape.decode_real(_dta[5]),
                                         layer=_dta[3],
                                        )
            return _ret_val

    class Arc(Wire):
        """ A struct that represents an arc
        """
        capmask = 0x10
        caps = {
                0x00: None,
                0x10: "flat",
               }
        directionmask = 0x20
        directions = {
                      0x00: "clockwise",
                      0x20: "counterclockwise",
                     }

        def __init__(self, x1, y1, x2, y2, layer, width, curve, cap, direction):
            """ Just a constructor
            """
            super(Eagle.Arc, self).__init__(x1, y1, x2, y2, layer, width)
            self.curve = curve
            self.cap = cap
            self.direction = direction
            return

        @staticmethod
        def parse(chunk):
            """ Parses arc
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Arc.template, chunk)
            
            _ret_val = Eagle.Arc(
                          x1=Eagle.Shape.decode_real(_dta[4] & 0xffffff),
                          y1=Eagle.Shape.decode_real(_dta[5] & 0xffffff),
                          x2=Eagle.Shape.decode_real(_dta[6] & 0xffffff),
                          y2=Eagle.Shape.decode_real(_dta[7]),
                                  layer=_dta[3],
                                  width=(Eagle.Wire.width_xscale *
                                         Eagle.Shape.decode_real(
                                                                _dta[8])),
# TODO decode curve...
                          curve=Eagle.Shape.decode_real(
                                  (_dta[4] & 0xff000000 >> 24) +
                                  (_dta[5] & 0xff000000 >> 16) +
                                  (_dta[6] & 0xff000000 >> 8)),
                          cap=Eagle.Arc.caps[_dta[9] & Eagle.Arc.capmask],
                          direction=Eagle.Arc.directions[_dta[9] & 
                                                Eagle.Arc.directionmask]
                                     )
            return _ret_val

    class Text(Shape):
        """ A struct that represents a text
        """
        constant = 0x31
        template = "=4B2IH4B6s"

        max_embed_len = 5
        delimeter = b'!'
        no_embed_str = b'\x7f'

        def __init__(self, value, x, y, size, layer, rotate, font, ratio):
            """ Just a constructor
            """
            super(Eagle.Text, self).__init__(layer)
            self.value = value
            self.x = x
            self.y = y
            self.size = size
            self.rotate = rotate
            self.font = font
            self.ratio = ratio
            return

        @staticmethod
        def parse(chunk):
            """ Parses text
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Text.template, chunk)

            _value = None
            if Eagle.Text.no_embed_str != _dta[11][0]:
                _value = _dta[11]
            _ret_val = Eagle.Text(value=_value,
                                     x=Eagle.Shape.decode_real(_dta[4]),
                                     y=Eagle.Shape.decode_real(_dta[5]),
                                     size=Eagle.Text.size_xscale *
                                          Eagle.Shape.decode_real(_dta[6]),
                                     layer=_dta[3],
                                     rotate=Eagle.Text.rotates[_dta[10]],
                                     font=Eagle.Text.fonts[_dta[2]],
                                     ratio=_dta[7] >> Eagle.Text.ratio_sscale,
                                    )
            return _ret_val

        @staticmethod
        def parse2(chunk):
            """ Parses string name
            """
            _ret_val = None

            _parts = chunk.split(Eagle.Text.delimeter)
            if 1 < len(_parts):
                logging.error("too many extra values for Text: " + chunk)

            _ret_val = _parts[0]

            return _ret_val

    class Label(Shape):
        """ A struct that represents a label
        """
        constant = 0x33
        template = "=4B2I2H4BI"

        mirroredmask = 0x10
        onoffmask = 0x01

        def __init__(self, x, y, size, layer, rotate, ratio, font, 
                     onoff, mirrored, xref=None):
            """ Just a constructor
            """
            super(Eagle.Label, self).__init__(layer)
            self.x = x
            self.y = y
            self.size = size
            self.xref = onoff
            self.rotate = rotate
            self.ratio = ratio
            self.font = font
            self.onoff = onoff
            self.mirrored = mirrored
            return #}}}

        @staticmethod
        def parse(chunk):
            """ Parses label
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Label.template, chunk)

            _ret_val = Eagle.Label(x=Eagle.Shape.decode_real(_dta[4]),
                                      y=Eagle.Shape.decode_real(_dta[5]),
                                      size=Eagle.Label.size_xscale *
                                           Eagle.Shape.decode_real(_dta[6]),
                                      layer=_dta[3],
#                                      xref=0,
                                      rotate=Eagle.Label.rotates[
                                              Eagle.Label.rotatemask & 
                                              _dta[9]],
                                      ratio=_dta[7] >> Eagle.Text.ratio_sscale,
                                      font=Eagle.Label.fonts[_dta[2]],
                                      onoff=(True if 0 != 
                                             _dta[10] & Eagle.Label.onoffmask
                                             else False),
                                      mirrored=(True if 0 != 
                                                _dta[9] & Eagle.Label.mirroredmask
                                                else False),
                                     )
            return _ret_val

    class Bus(Web):
        """ A struct that represents a web
        """
        constant = 0x3a
        template = "=2BH8s3I"

        def __init__(self, name, numofblocks=0, segments=None):
            """ Just a constructor
            """
            super(Eagle.Bus, self).__init__(name, numofblocks, segments)
            return

        @staticmethod
        def parse(chunk):
            """ Parses bus
            """
            _ret_val = None

            _dta = struct.unpack(Eagle.Bus.template, chunk)

            _ret_val = Eagle.Bus(name=_dta[3],
                                    numofblocks=_dta[2],
                                   )
            return _ret_val

    class Attribute:
        """ A struct that represents an attribute
        """
        constant = 0x42
        template = "=3BI17s"

        max_embed_len = 17
        delimeter = b'!'
        no_embed_str = b'\x7f'

        def __init__(self, name, value):
            """ Just a constructor
            """
            self.name = name
            self.value = value
            return

        @staticmethod
        def _parse(string):
            """ Splits string in parts
            """
            (_name, _value) = (None, None)

            _parts = string.split(Eagle.Attribute.delimeter)

            _name = _parts[0]
            if 2 > len(_parts):
                pass # strange embedded attribute
            else:
                _value = Eagle.Attribute.delimeter.join(_parts[1:])

            return (_name, _value)

        @staticmethod
        def parse(chunk):
            """ Parses block attribute
            """
            _ret_val = None
            (_name, _value) = (None, None)

            _dta = struct.unpack(Eagle.Attribute.template, chunk)

            if Eagle.Attribute.no_embed_str != _dta[4][0]: # embedded attr
                (_name, _value) = Eagle.Attribute._parse(_dta[4])
            else:
# TODO decode [8] [9] [10]
# [11] -- a kind of a marker, 0x09; 4 bytes long int, changed on each save as, even with no changes
                pass

            _ret_val = Eagle.Attribute(name=_name,
                                          value=_value
                                         )
            return _ret_val

        @staticmethod
        def parse2(chunk):
            """ Parses string attribute
            """
            _ret_val = None

            (_name, _value) = Eagle.Attribute._parse(chunk)
            _ret_val = Eagle.Attribute(name=_name,
                                          value=_value
                                         )
            return _ret_val

    class Schematic:
        """ A struct that represents "schematic"
        """
        defxreflabel = ":%F%N/%S.%C%R"
        defxrefpart = "/%S.%C%R"

        delimeter = b'\t'

        def __init__(self, xreflabel=None, xrefpart=None):
            """ Just a constructor
            """
            if None == xreflabel:
                xreflabel = Eagle.Schematic.defxreflabel
            if None == xrefpart:
                xrefpart = Eagle.Schematic.defxrefpart

            self.xreflabel = xreflabel
            self.xrefpart = xrefpart
            return

        @staticmethod
        def parse(chunk):
            """ Parses string attribute
            """
            _ret_val = None
            (_xreflabel, _xrefpart) = (None, None)

            _parts = chunk.split(Eagle.Schematic.delimeter)
            _xreflabel = _parts[0]

            if 2 != len(_parts):
                logging.error("strange schematic string: " + chunk)
            else:
                _xrefpart = _parts[1]

            _ret_val = Eagle.Schematic(xreflabel=_xreflabel,
                                          xrefpart=_xrefpart
                                         )
            return _ret_val

    class NetClass:
        """ A struct that represents a net class
        """
        template0 = "=3I" # header part read by _parse_file
        template1 = "=13I" # unpack the rest of chunk
        template2x = "=3I%ss13I" # pack the whole thing

        scale1 = 10000.0

        constant = 0x20000425
        constantmid = 0x87654321
        constantend = 0x89abcdef
        
        endmarker = 0x99999999

        def __init__(self, num, name='', width=0, drill=0, clearances=[], 
                     leadint=0):
            """ Just a constructor
            """ 
            self.num = num
            self.name = name
            self.width = width
            self.drill = drill
            self.clearances = clearances
            
            self.leadint = leadint # TODO decypher it..
            return

        @staticmethod
        def decode_real(number):
            """ Transforms given binary array to a float
            """
            _ret_val = 0
            _ret_val = number / Eagle.NetClass.scale1
            return _ret_val

        @staticmethod
        def parse(leadint, ncconst, chunk):
            """ Parses rectangle
            """
            _ret_val = None

            if Eagle.NetClass.constant == ncconst and None != chunk:
                _name = chunk.split('\0')[0]
                _foff = 1 + len(_name)

                _dta = struct.unpack("13I", chunk[_foff:])

                if (Eagle.NetClass.constantmid == _dta[1] and
                        Eagle.NetClass.constantend == _dta[12]):
                    if 0 < len(_name): # used netclass
                        _ret_val = Eagle.NetClass(
                                 num=_dta[0],
                                 name=_name, 
                                 width=Eagle.NetClass.decode_real(_dta[2]),
                                 drill=Eagle.NetClass.decode_real(_dta[3]),
                                 clearances = [
                                     (_nn, 
                                      Eagle.NetClass.decode_real(
                                                                _dta[4 + _nn])
                                     ) 
                                     for _nn in range(1 + _dta[0])
                                     if 0 != _dta[4 + _nn]
                                 ],
                                 leadint=leadint
                                                    )
                    else: # unused netclass
                        _ret_val = Eagle.NetClass(num=_dta[0], 
                                                     leadint=leadint)
                else:
                    logging.error("bad constants or/and data in netclasses")
            elif Eagle.NetClass.ncendmarker == ncconst and None == chunk:
                pass # nothing to do: final entry ; never hit though
            else:
                logging.error("bad constants or/and data in netclasses")
            return _ret_val

    blocksize = 24
    noregblockconst = b'\x13\x12\x99\x19'
    noregdelimeter = b'\0'

    def __init__(self):
        """ Basic initilaization
        """
        self.header = None
        self.layers = []
        self.settings = []
        self.grid = None
        self.attributeheader = None
        self.attributes = []
        self.shapeheader = None
        self.shapes = []
        self.nets = []
        self.buses = []
        self.texts = []
        self.schematic = None
        self.netclasses = []
        return

    def _parse(self, filehandle):
        """ Parse an Eagle file into a set of Eagle objects
        """
# headers (constant block size driven)
        self.header = self.Header.parse(filehandle.read(self.blocksize))
# to keep parsing position
        _cur_web = None # consists of one or more segments
        _cur_segment = None # consists of one or more "wires"

        for _nn in range(-1 + self.header.numofblocks):
            _dta = filehandle.read(self.blocksize)

            _type = struct.unpack("24B", _dta)[0]
            if Eagle.Settings.constant == _type:
                self.settings.append(self.Settings.parse(_dta))
            elif Eagle.Grid.constant == _type:
                self.grid = self.Grid.parse(_dta)
            elif Eagle.Layer.constant == _type:
                self.layers.append(self.Layer.parse(_dta))
            elif Eagle.AttributeHeader.constant == _type:
                self.attributeheader = self.AttributeHeader.parse(_dta)
            elif Eagle.ShapeHeader.constant == _type:
                self.shapeheader = self.ShapeHeader.parse(_dta)
            elif Eagle.Circle.constant == _type:
                self.shapes.append(self.Circle.parse(_dta))
            elif Eagle.Rectangle.constant == _type:
                self.shapes.append(self.Rectangle.parse(_dta))
            elif Eagle.Net.constant == _type:
                _cur_web = self.Net.parse(_dta)
                self.nets.append(_cur_web)
            elif Eagle.Segment.constant == _type:
                _cur_segment = self.Segment.parse(_dta)
                _cur_web.segments.append(_cur_segment)
            elif Eagle.Wire.constant == _type:
                _cur_segment.wires.append(self.Wire.parse(_dta))
            elif Eagle.Junction.constant == _type:
                _cur_segment.junctions.append(self.Junction.parse(_dta))
            elif Eagle.Label.constant == _type:
                _cur_segment.labels.append(self.Label.parse(_dta))
            elif Eagle.Bus.constant == _type:
                _cur_web = self.Bus.parse(_dta)
                self.buses.append(_cur_web)
            elif Eagle.Text.constant == _type:
                self.texts.append(self.Text.parse(_dta))
            elif Eagle.Attribute.constant == _type:
                self.attributes.append(self.Attribute.parse(_dta))
            else:
# TODO remove
                print("unknown block tag %s" % hex(_type))

# desc (length driven)
        _noregblockheader = filehandle.read(4)
        if Eagle.noregblockconst != _noregblockheader:
# TODO remove
            print("bad constant follows headers!")

        # read len in bytes, then read corrsponding number of bytes
        _unreg_dta = filehandle.read(struct.unpack("I", 
                            filehandle.read(4))[0]).split(self.noregdelimeter) 

        if 5 <= float(self.header.version):
            self.schematic = Eagle.Schematic.parse(_unreg_dta[0])
            _ndx = 1
        else: # no schematic strings; looks like they're introduced recently
            self.schematic = Eagle.Schematic()
            _ndx = 0

# other items are strings: attributes, texts, ..something else?
        for _aa in _unreg_dta[_ndx:]:
            if 0 < len(_aa):
                _attr = Eagle.Attribute.parse2(_aa)

                if None != _attr.name:
                    for (_nn, _ab) in enumerate(self.attributes):
                        if None == _ab.name:
                            self.attributes[_nn] = _attr
                            break
                    else:
                        _name = Eagle.Text.parse2(_aa)
                        for _tt in self.texts:
                            if None == _tt.value:
                                _tt.value = _name
                        else:
# TODO remove
                            print("no room for extra attribute " + str(_attr))
            else:
                break # NoOP: last item is just a b'\0'

# just to note: the list above ends with two zero bytes

        while True: # netclasses ## 0..7
            (_some_int, _ncconst, _nclen) = struct.unpack(
                    self.NetClass.template0, 
                    filehandle.read(struct.calcsize(self.NetClass.template0)))
            _ncdta = None
            if 0 < _nclen:
                _ncdta = filehandle.read(_nclen)
            else:
                break # should leadnum of a final 3I block be saved?..
            self.netclasses.append(self.NetClass.parse(_some_int, 
                                                       _ncconst, _ncdta))
 
    def _convert(self):
        """ Converts a set of Eagle objects into Design
        """
        design = Design()

        return design

    def parse(self, filename):
        """ Parse an Eagle file into a design """
        design = None

        with open(filename, 'rb') as _if:
            self._parse(_if)

        design = self._convert()

        return design


