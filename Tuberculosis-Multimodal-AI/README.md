# Multimodal AI Pipeline for Tuberculosis Classification

This project explore pulmonary tuberculosis (PTB) classification by combining chest X-ray (CXR) images with clinical text notes.

### Pipeline
1. **Lung segmentation:** train a U-Net on CXRs with available masks and predict missing masks.
2. **Image preparation:** apply the masks to focus on the lung regions.
3. **Text features:** extract sentence embeddings from clinical notes using spaCy (`en_core_web_md`).
4. **Classification:** use VGG16 image features and compare image-only and image–text models, with concatenation and summation as fusion strategies.

The experiments compare different fusion approaches and evaluate whether adding text improves performance over images alone.

## Notebooks

- `Subtask_1e2.ipynb` – train the segmenter and prepare segmented images.
- `Subtask_3.ipynb` – extract text features.
- `Subtask_4.ipynb` – train and evaluate concatenation-based fusion.
- `Subtask_4sum.ipynb` – train and evaluate summation-based fusion.
