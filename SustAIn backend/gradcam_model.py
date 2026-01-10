import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

model = models.resnet18(pretrained=True)
model.eval()

def get_gradcam_score(image_path):
    """
    Returns normalized Grad-CAM score (0-1)
    """
    transform = transforms.Compose([
        transforms.Resize((224,224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
    ])
    img = Image.open(image_path).convert("RGB")
    x = transform(img).unsqueeze(0)
    with torch.no_grad():
        outputs = model(x)
        prob = nn.Softmax(dim=1)(outputs)
        top_prob = prob.max().item()
    gradcam_score = 1 - top_prob
    return gradcam_score
