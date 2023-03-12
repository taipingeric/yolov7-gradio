import torch
import gradio as gr
import cv2
import numpy as np
import random
import numpy as np
from models.experimental import attempt_load
from utils.general import check_img_size, non_max_suppression, \
    scale_coords
from utils.plots import plot_one_box
from utils.torch_utils import time_synchronized
import time



def letterbox(im, new_shape=(640, 640), color=(114, 114, 114), auto=True, scaleup=True, stride=32):
    # Resize and pad image while meeting stride-multiple constraints
    shape = im.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # only scale down, do not scale up (for better val mAP)
        r = min(r, 1.0)

    # Compute padding
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding

    if auto:  # minimum rectangle
        dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)  # add border
    return im, r, (dw, dh)

# names = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light', 
#          'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 
#          'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 
#          'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 
#          'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 
#          'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 
#          'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone', 
#          'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 
#          'hair drier', 'toothbrush']
names = ['healthy', 'mild', 'medium', 'severe']

# 綠 青 紅 紫
colors = [[0, 255, 0], [0, 255, 255], [255, 0, 0], [177, 91, 255]] 

# Init model
print("Init model")

# Load model
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu') 
model_path = 'weights/yolov7.pt'
model = attempt_load(model_path, map_location=device)

def detect(img,model,device,iou_threshold=0.45,confidence_threshold=0.25):   
    imgsz = 640
    img = np.array(img)
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size

    # Get names and colors
    names = model.module.names if hasattr(model, 'module') else model.names

    # Run inference
    imgs = img.copy()  # for NMS
    
    image, ratio, dwdh = letterbox(img, auto=False)
    image = image.transpose((2, 0, 1))
    img = torch.from_numpy(image).to(device)
    img = img.float()  # uint8 to fp16/32
    img /= 255.0  # 0 - 255 to 0.0 - 1.0
    if img.ndimension() == 3:
        img = img.unsqueeze(0)


    # Inference
    t1 = time_synchronized()
    start = time.time()
    with torch.no_grad():   # Calculating gradients would cause a GPU memory leak
        pred = model(img,augment=True)[0]
    fps_inference = 1/(time.time()-start)
    t2 = time_synchronized()

    # Apply NMS
    pred = non_max_suppression(pred, confidence_threshold, iou_threshold, classes=None, agnostic=True)
    t3 = time_synchronized()

    for i, det in enumerate(pred):  # detections per image
        if len(det):
            # Rescale boxes from img_size to im0 size
            det[:, :4] = scale_coords(img.shape[2:], det[:, :4], imgs.shape).round()


            # Write results
            for *xyxy, conf, cls in reversed(det):
                label = f'{names[int(cls)]} {conf:.2f}'
                plot_one_box(xyxy, imgs, label=label, color=colors[int(cls)], line_thickness=2)

    return imgs,fps_inference

def inference(img,model_link,iou_threshold,confidence_threshold):
    print(model_link)
    return detect(img,model,device,iou_threshold,confidence_threshold)


def inference2(video,model_link,iou_threshold,confidence_threshold):
    print(model_link)
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    # Load model
    model_path = 'weights/'+str(model_link)+'.pt'
    model = attempt_load(model_path, map_location=device) 
    frames = cv2.VideoCapture(video)
    fps = frames.get(cv2.CAP_PROP_FPS)
    image_size = (int(frames.get(cv2.CAP_PROP_FRAME_WIDTH)),int(frames.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    finalVideo = cv2.VideoWriter('output.mp4',cv2.VideoWriter_fourcc(*'VP90'), fps, image_size)
    fps_video = []
    while frames.isOpened():
        ret,frame = frames.read()
        if not ret:
            break
        frame,fps = detect(frame,model,device,iou_threshold,confidence_threshold)
        fps_video.append[fps]
        finalVideo.write(frame)
    frames.release()
    finalVideo.release()
    return 'output.mp4',np.mean(fps_video)



examples_images = ['data/images/non_perio_1021.tif_0.png', 'data/images/non_perio_1035.tif_0.png', 'data/images/non_perio_1043.tif_0.png', 
                   'data/images/non_perio_1059.tif_0.png', 'data/images/non_perio_669.tif_0.png', 'data/images/non_perio_684.tif_0.png', 
                   'data/images/perio_2136.tif_0.png', 'data/images/perio_2137.tif_0.png', 'data/images/perio_2466.tif_0.png', 
                   'data/images/perio_2471.tif_0.png', 'data/images/perio_2827.tif_0.png', 'data/images/perio_2932.tif_0.png']

examples_videos = [] 

models = ['yolov7']
# models = ['yolov7','yolov7x','yolov7-w6','yolov7-d6','yolov7-e6e']

with gr.Blocks() as demo:
    gr.Markdown("## 經國管理暨健康學院")
    gr.Markdown("## 環口X-ray影像於牙周骨質流失之AI判讀應用")
    with gr.Tab("Image"):
        gr.Markdown("## 請輸入環口X-ray影像")
        with gr.Row():
            image_input = gr.Image(type='pil', label="Input Image", source="upload")
            image_output = gr.Image(type='pil', label="Output Image", source="upload")
        fps_image = gr.Number(0,label='FPS')
        image_drop = gr.Dropdown(choices=models,value=models[0])
        image_iou_threshold = gr.Slider(label="IOU Threshold",interactive=True, minimum=0.0, maximum=1.0, value=0.45)
        image_conf_threshold = gr.Slider(label="Confidence Threshold",interactive=True, minimum=0.0, maximum=1.0, value=0.25)
        gr.Examples(examples=examples_images,
                    inputs=image_input,
                    outputs=image_output,
                    examples_per_page=6)
        text_button = gr.Button("牙周骨質流失偵測")
#     with gr.Tab("Video"):
#         gr.Markdown("## YOLOv7 Inference on Video")
#         with gr.Row():
#             video_input = gr.Video(type='pil', label="Input Image", source="upload")
#             video_output = gr.Video(type="pil", label="Output Image",format="mp4")
#         fps_video = gr.Number(0,label='FPS')
#         video_drop = gr.Dropdown(choices=models,value=models[0])
#         video_iou_threshold = gr.Slider(label="IOU Threshold",interactive=True, minimum=0.0, maximum=1.0, value=0.45)
#         video_conf_threshold = gr.Slider(label="Confidence Threshold",interactive=True, minimum=0.0, maximum=1.0, value=0.25)
#         gr.Examples(examples=examples_videos,inputs=video_input,outputs=video_output)
#         video_button = gr.Button("Detect")
    
#     with gr.Tab("Webcam Video"):
#         gr.Markdown("## YOLOv7 Inference on Webcam Video")
#         gr.Markdown("Coming Soon")

    text_button.click(inference, inputs=[image_input,image_drop,
                                         image_iou_threshold,image_conf_threshold],
                                        outputs=[image_output,fps_image])
#     video_button.click(inference2, inputs=[video_input,video_drop,
#                                            video_iou_threshold,video_conf_threshold],            
#                                         outputs=[video_output,fps_video])

demo.launch(share=True)
