import os
import torch
from torchvision import transforms
import torch.nn.functional as F
import numpy as np

from model.inspyrenet import InSPyReNet_SwinB, InSPyReNet_Res2Net50

# aws_efs_path = r"/mnt/efs/remove_bg/ckpt"
aws_efs_path = r"./model/ckpt"

class RemoveBackGround:
    def __init__(self, backbone="swinB", device=None, types="map"):
        self.meta = {'base_size': (384, 384),
                    'threshold': 512,
                    'ckpt_name': os.path.join(aws_efs_path, f"ckpt_{backbone}.pth")}
        
        if backbone == "swinB":
            self.model = InSPyReNet_SwinB(depth=64, **self.meta)
        elif backbone == "resnet":
            self.model = InSPyReNet_Res2Net50(depth=64, pretrained=False, **self.meta)
        else:
            print("No such model backbone")
            raise AssertionError

        if device is not None:
            self.device = device
        else:
            self.device = "cpu"

        self.model.eval()
        self.model.load_state_dict(torch.load(self.meta["ckpt_name"], map_location=torch.device(device)), strict=True)
        self.model = self.model.to(self.device)

        self.transform = transforms.Compose([transforms.Resize(self.meta["base_size"]),
                                             transforms.ToTensor(),])
        
        self.types = types

        print(f"import model succes, device={self.device}")

    def process(self, img):
        shape = img.size[::-1]
        x = self.transform(img)
        x = x.unsqueeze(0)
        x = x.to(self.device)

        with torch.no_grad():
            pred = self.model(x)
        
        pred = F.interpolate(pred, shape, mode="bilinear", align_corners=True)
        pred = pred.data.cpu()
        pred = pred.numpy().squeeze()

        img = np.array(img)

        if self.types == 'map':
            img = (np.stack([pred] * 3, axis=-1) * 255)

        return img.astype(np.uint8)
    
if __name__ == "__main__":
    from PIL import Image
    import time
    image = Image.open("3840_2400_bagandproduct.jpg")

    start_time = time.time()
    remover = RemoveBackGround(backbone="swinB", device="cpu")
    result = remover.process(image)
    end_time = time.time()

    print(end_time - start_time)
    Image.fromarray(result).save("test_result.png")
