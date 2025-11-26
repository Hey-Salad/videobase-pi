"""
Hailo AI Inference Module for Multi-Camera RTSP System
Runs object detection using Hailo-8L accelerator
"""
import logging
import numpy as np
import time
from typing import Dict, List, Optional, Tuple
from hailo_platform import (
    VDevice,
    HailoStreamInterface,
    InferVStreams,
    ConfigureParams,
    FormatType,
    HailoRTException
)

logger = logging.getLogger(__name__)


class HailoDetector:
    """Hailo-based object detection for RTSP streams"""

    # COCO class names (80 classes for YOLO models)
    COCO_CLASSES = [
        'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
        'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
        'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
        'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
        'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
        'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
        'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
        'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
        'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
        'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
    ]

    def __init__(
        self,
        hef_path: str = "/usr/share/hailo-models/yolov8s_h8l.hef",
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640)
    ):
        """
        Initialize Hailo detector

        Args:
            hef_path: Path to the HEF model file
            confidence_threshold: Minimum confidence for detections
            nms_threshold: NMS IoU threshold
            input_size: Model input size (width, height)
        """
        self.hef_path = hef_path
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size

        # Performance metrics
        self.inference_times = []
        self.total_inferences = 0

        logger.info(f"Initializing Hailo detector with model: {hef_path}")

        try:
            # Initialize Hailo device
            self.device = VDevice()

            # Load HEF model
            with open(hef_path, 'rb') as f:
                hef_data = f.read()

            # Create network group
            network_group = self.device.configure(ConfigureParams.create_from_hef(hef_data, interface=HailoStreamInterface.PCIe))[0]
            self.network_group = network_group

            # Get input/output info
            self.input_vstreams_params = network_group.make_input_vstream_params()
            self.output_vstreams_params = network_group.make_output_vstream_params()

            logger.info("Hailo detector initialized successfully")
            logger.info(f"Model input shape: {self.input_size}")

        except Exception as e:
            logger.error(f"Failed to initialize Hailo detector: {e}")
            raise

    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for Hailo inference

        Args:
            frame: BGR frame from camera (H, W, 3)

        Returns:
            Preprocessed frame ready for inference
        """
        import cv2

        # Resize to model input size
        resized = cv2.resize(frame, self.input_size)

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1] if needed (depends on model)
        # Most Hailo models expect uint8 input
        return rgb

    def postprocess_detections(
        self,
        raw_output: List[np.ndarray],
        original_shape: Tuple[int, int]
    ) -> List[Dict]:
        """
        Postprocess raw Hailo output to detection format

        Args:
            raw_output: Raw output from Hailo inference
            original_shape: Original frame (height, width)

        Returns:
            List of detection dicts with format:
            {
                'bbox': [x, y, w, h],
                'confidence': float,
                'class_id': int,
                'label': str
            }
        """
        detections = []

        # Note: YOLOv8 Hailo output format varies by model
        # This is a simplified version - adjust based on your specific model
        try:
            # Typical YOLOv8 output: [batch, num_detections, 85]
            # 85 = x, y, w, h, confidence, 80 class scores

            if len(raw_output) > 0:
                output_tensor = raw_output[0]

                # Reshape if needed
                if len(output_tensor.shape) == 3:
                    output_tensor = output_tensor[0]  # Remove batch dimension

                # Filter by confidence
                for detection in output_tensor:
                    if len(detection) >= 5:
                        x, y, w, h, conf = detection[:5]

                        if conf >= self.confidence_threshold:
                            # Get class scores if available
                            class_id = 0
                            if len(detection) > 5:
                                class_scores = detection[5:]
                                class_id = int(np.argmax(class_scores))

                            # Scale coordinates back to original image
                            orig_h, orig_w = original_shape
                            x_scale = orig_w / self.input_size[0]
                            y_scale = orig_h / self.input_size[1]

                            detections.append({
                                'bbox': [
                                    float(x * x_scale),
                                    float(y * y_scale),
                                    float(w * x_scale),
                                    float(h * y_scale)
                                ],
                                'confidence': float(conf),
                                'class_id': class_id,
                                'label': self.COCO_CLASSES[class_id] if class_id < len(self.COCO_CLASSES) else f'class_{class_id}'
                            })

        except Exception as e:
            logger.error(f"Error in postprocessing: {e}")

        return detections

    def infer(self, frame: np.ndarray) -> Tuple[List[Dict], float]:
        """
        Run inference on a frame

        Args:
            frame: BGR image from camera

        Returns:
            Tuple of (detections, inference_time_ms)
        """
        start_time = time.time()

        try:
            # Preprocess
            preprocessed = self.preprocess_frame(frame)
            original_shape = frame.shape[:2]

            # Create input data
            input_data = {self.input_vstreams_params[0].name: np.expand_dims(preprocessed, axis=0)}

            # Run inference
            with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
                output = infer_pipeline.infer(input_data)
                raw_output = list(output.values())

            # Postprocess
            detections = self.postprocess_detections(raw_output, original_shape)

            # Calculate inference time
            inference_time = (time.time() - start_time) * 1000  # ms

            # Update metrics
            self.inference_times.append(inference_time)
            if len(self.inference_times) > 100:
                self.inference_times.pop(0)
            self.total_inferences += 1

            return detections, inference_time

        except Exception as e:
            logger.error(f"Inference error: {e}")
            return [], 0.0

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        if not self.inference_times:
            return {
                'avg_inference_time_ms': 0,
                'fps': 0,
                'total_inferences': 0
            }

        avg_time = np.mean(self.inference_times)
        return {
            'avg_inference_time_ms': round(avg_time, 2),
            'fps': round(1000 / avg_time if avg_time > 0 else 0, 2),
            'total_inferences': self.total_inferences,
            'min_time_ms': round(np.min(self.inference_times), 2),
            'max_time_ms': round(np.max(self.inference_times), 2)
        }

    def cleanup(self):
        """Release Hailo resources"""
        logger.info("Cleaning up Hailo detector")
        try:
            if hasattr(self, 'network_group'):
                # Release network group
                pass
            if hasattr(self, 'device'):
                # Release device
                pass
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def format_detections_for_frontend(
    detections: List[Dict],
    frame_shape: Tuple[int, int],
    inference_time: float,
    total_count: int
) -> Dict:
    """
    Format Hailo detections for frontend consumption

    Args:
        detections: List of detection dicts
        frame_shape: (height, width) of original frame
        inference_time: Inference time in ms
        total_count: Total inference count

    Returns:
        Dict in format expected by frontend
    """
    height, width = frame_shape

    # Convert to frontend format
    boxes = []
    labels = []

    for det in detections:
        bbox = det['bbox']
        # Format: [x, y, w, h, class_id, confidence]
        boxes.append([
            bbox[0],  # x
            bbox[1],  # y
            bbox[2],  # width
            bbox[3],  # height
            det['class_id'],
            int(det['confidence'] * 100)  # confidence as percentage
        ])
        labels.append(det['label'])

    return {
        'boxes': boxes,
        'labels': labels,
        'resolution': [width, height],
        'count': total_count,
        'perf': [[0, int(inference_time), len(detections)]],  # [stage, time_ms, detections]
        'image': ''  # Not sending full image
    }
