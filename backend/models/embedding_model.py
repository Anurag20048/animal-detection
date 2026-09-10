from typing import Dict, Optional
import numpy as np
from utils.similarity import normalize_embedding

class ResNet50EmbeddingModel:
    def __init__(self, use_pretrained: bool = True) -> None:
        try:
            import torch
            import torch.nn as nn
            from torchvision import models, transforms
            from torchvision.models import ResNet50_Weights
        except Exception as exc:
            raise RuntimeError("torch and torchvision are required for biometric embeddings.") from exc
        self.torch = torch
        self.transforms = transforms
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        weights = None
        if use_pretrained:
            try:
                weights = ResNet50_Weights.DEFAULT
                self.model = models.resnet50(weights=weights)
            except Exception:
                self.model = models.resnet50(weights=None)
                weights = None
        else:
            self.model = models.resnet50(weights=None)
        self.model.fc = nn.Identity()
        self.model.eval().to(self.device)
        self.preprocess = weights.transforms() if weights is not None else transforms.Compose([
            transforms.ToPILImage(), transforms.Resize((224, 224)), transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])

    def embed(self, image: np.ndarray) -> Optional[np.ndarray]:
        if image is None or image.size == 0: return None
        import cv2
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        tensor = self.preprocess(rgb_image).unsqueeze(0).to(self.device)
        with self.torch.no_grad():
            embedding = self.model(tensor).squeeze(0).detach().cpu().numpy()
        return normalize_embedding(embedding)

    def embed_regions(self, images: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        embeddings: Dict[str, np.ndarray] = {}
        for region, image in images.items():
            embedding = self.embed(image)
            if embedding is not None: embeddings[region] = embedding
        return embeddings
