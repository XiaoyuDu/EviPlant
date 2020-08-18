import pyvhdi
import pytsk3

class vhdi_Img_Info(pytsk3.Img_Info):
  def __init__(self, vhdi_file):
    self._vhdi_file = vhdi_file
    super(vhdi_Img_Info, self).__init__(
        url='', type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

  def close(self):
    self._vhdi_file.close()

  def read(self, offset, size):
    self._vhdi_file.seek(offset)
    return self._vhdi_file.read(size)

  def get_size(self):
    return self._vhdi_file.get_media_size()

vhdi_file = pyvhdi.file()
vhdi_file.open("Windows7-Original.vhd")
img_info = vhdi_Img_Info(vhdi_file)
partitionTable = pytsk3.Volume_Info(img_info)
for partition in partitionTable:
  print partition.addr, partition.desc, "%ss(%s)" % (partition.start, partition.start * 512), partition.len