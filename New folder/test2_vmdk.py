import pyvmdk
import pytsk3


class vmdk_Img_Info(pytsk3.Img_Info):
  def __init__(self, vmdk_handle):
    self._vmdk_handle = vmdk_handle
    super(vmdk_Img_Info, self).__init__(
        url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

  def close(self):
    self._vmdk_handle.close()

  def read(self, offset, size):
    self._vmdk_handle.seek(offset)
    return self._vmdk_handle.read(size)

  def get_size(self):
    return self._vmdk_handle.get_media_size()


vmdk_handle = pyvmdk.handle()

# help(pyvmdk.handle)

vmdk_handle.open("win7.vmdk")
vmdk_handle.open_extent_data_files()

img_info = vmdk_Img_Info(vmdk_handle)

fs_info = pytsk3.FS_Info(img_info, offset=63 * 512)