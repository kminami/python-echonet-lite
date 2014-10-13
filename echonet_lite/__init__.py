# -*- coding: utf-8 -*-

import socket

class Frame:
  ''' ECHONET Lite Frame'''

  ESV_STR = {
    0x60: 'SetI',     0x61: 'SetC',     0x62: 'Get',     0x63: 'INF_REQ',                                 0x6E: 'SetGet',
                      0x71: 'Set_Res',  0x72: 'Get_Res', 0x73: 'INF',     0x74: 'INFC', 0x7A: 'INFC_Res', 0x7E: 'SetGet_Res',
    0x50: 'SetI_SNA', 0x51: 'SetC_SNA', 0x52: 'Get_SNA', 0x53: 'INF_SNA',                                 0x5E: 'SetGet_SNA'
  }

  def __init__(self, data):
    if type(data) == bytearray:
      self._decode(data)
    elif type(data) == list:
      if len(data) < 6:
        self.valid = False
        return
      self.protocol_type = 'ECHONET_Lite'
      self.format = '1'
      self.EHD1 = data[0]
      self.EHD2 = data[1]
      self.TID = data[2]
      self.SEOJ = data[3]
      self.DEOJ = data[4]
      self.ESV = data[5]
      self.properties = []
      self.valid = True
    else:
      self.valid = False

  def _decode(self, data):
    if len(data) < 12:
      self.valid = False
      return
    self._decode_header(data[0:4])
    self._decode_data(data[4:])
    self.valid = True

  def _decode_header(self, data):
    self.EHD1 = data[0]
    self.EHD2 = data[1]
    self.TID = data[2:4]
    if self.EHD1 == 0x10:
      self.protocol_type = 'ECHONET_Lite'
    elif self.EHD1 >= 0x80:
      self.protocol_type = 'ECHONET'
    else:
      self.protocol_type = 'UNKNOWN'
    if self.EHD2 == 0x81:
      self.format = '1'
    elif self.EHD2 == 0x82:
      self.format = '2'
    else:
      self.format = 'UNKNOWN'

  def _decode_data(self, data):
    self.SEOJ = data[0:3]
    self.DEOJ = data[3:6]
    self.ESV = data[6]
    num_of_properties = data[7] # OPC
    self.properties = []
    offset = 8
    for i in range(num_of_properties):
      prop = Property(data[offset:])
      self.properties.append(prop)
      offset += len(prop)

  @staticmethod
  def create_response(frame):
    if frame.ESV == 0x61: # SetC
      ESV = 0x71
    elif frame.ESV == 0x62: # Get
      ESV = 0x72
    else:
      return Frame()
    return Frame([frame.EHD1, frame.EHD2, frame.TID, frame.DEOJ, frame.SEOJ, ESV])

  def get_bytes(self):
    array = bytearray([self.EHD1, self.EHD2])
    array = array + self.TID + self.SEOJ + self.DEOJ
    array.append(self.ESV)
    array.append(len(self.properties)) # OPC
    for prop in self.properties:
      array = array + prop.get_bytes()
    return bytearray(array)

  def __str__(self):
    if not self.valid:
      return "echonet_lite.Frame(invalid)"
    return "echonet_lite.Frame(protocol_type={}, format={}, TID={}, SEOJ={}, DEOJ={}, ESV={}, OPC={})".format(
      self.protocol_type, self.format, repr(self.TID), repr(self.SEOJ), repr(self.DEOJ),
      Frame.ESV_STR[self.ESV] if self.ESV in Frame.ESV_STR else '0x{:x}'.format(self.ESV), len(self.properties)
    )

class Property:
  ''' ECHONET Property '''

  def __init__(self, data):
    if type(data) == bytearray:
      self.EPC = data[0]
      len_edt = data[1]
      self.EDT = data[1:1+len_edt]
    elif type(data) == list:
      self.EPC = data[0]
      self.EDT = data[1]
  
  def get_bytes(self):
    array = bytearray([self.EPC, len(self.EDT)])
    array = array + self.EDT
    return array

  def __len__(self):
    return 2 + len(self.EDT)

  def __str__(self):
    return 'echonet_lite.Property(EPC=0x{:x}, PDC={}, EDT={})'.format(self.EPC, len(self.EDT), repr(self.EDT))

class Object:
  ''' ECHONET Object '''

  def __init__(self, group, cls):
    self.group = group
    self.cls = cls
    self.id = None
    self.EOJ = None

  def set_instance_id(self, id):
    self.id = id
    self.EOJ = bytearray([self.group, self.cls, self.id])

  def service(self):
    pass

class GeneralLighting(Object):
  ''' General Lighting Object (group=0x02, class=0x90) '''

  def __init__(self):
    Object.__init__(self, 0x02, 0x90)

  def service(self, frame):
    if frame.ESV == 0x61: # SetC
      new_frame = Frame.create_response(frame)
      for prop in frame.properties:
        if prop.EPC == 0x80: # power (0x30=ON, 0x31=OFF)
          new_frame.properties.append(prop)
      return new_frame

class Node:
  ''' ECHONET Lite Node '''

  def __init__(self):
    self.objects = {}

  def add_object(self, obj):
    if obj.group not in self.objects:
      self.objects[obj.group] = {}
    if obj.cls not in self.objects[obj.group]:
      self.objects[obj.group][obj.cls] = []
    my_class = self.objects[obj.group][obj.cls]
    my_class.append(obj)
    obj.set_instance_id(len(my_class))

  def _deliver(self, frame):
    if frame.DEOJ == bytearray(b'\x0e\xf0\01'):
      return self.service(frame)
    group = frame.DEOJ[0]
    cls = frame.DEOJ[1]
    id = frame.DEOJ[2]
    if group in self.objects and cls in self.objects[group]:
      if id == 0:
        return # TODO: broadcast to this class
      if id <= len(self.objects[group][cls]):
        return self.objects[group][cls][id-1].service(frame)

  def service(self, frame):
    if frame.ESV == 0x62: # Get
      new_frame = Frame.create_response(frame)
      for prop in frame.properties:
        if prop.EPC == 0xd6: # instance list
          new_frame.properties.append(self._create_object_list_property())
      return new_frame

  def _create_object_list_property(self):
    array = [0]
    for group in self.objects:
      for cls in self.objects[group]:
        for id in range(1, len(self.objects[group][cls])+1):
          array += [group, cls, id]
          array[0] += 1
    return Property([0xd6, bytearray(array)])

  def _bind_socket(self):
    local_address = '0.0.0.0'
    multicast_group = '224.0.23.0'
    port = 3610
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((local_address, port))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(multicast_group) + socket.inet_aton(local_address))
    return sock
  
  def loop(self, debug=False):
    sock = self._bind_socket()
    print "wait..."
    while True:
      recv_msg, addr = sock.recvfrom(1024)
      if debug:
        print addr
      frame = Frame(bytearray(recv_msg))
      if debug:
        print_frame(frame)
      new_frame = self._deliver(frame)
      if new_frame is not None:
        if debug:
          print_frame(new_frame)
        sock.sendto(new_frame.get_bytes(), addr)

def print_frame(frame):
  print frame
  for prop in frame.properties:
    print prop
  print repr(frame.get_bytes())
