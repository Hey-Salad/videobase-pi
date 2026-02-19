"""
AI Agent Workflows for Video Skill Service
Provides natural language interfaces and automated workflows for OpenClaw AI
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ============================================================================
# Workflow Definitions
# ============================================================================

class WorkflowType(str, Enum):
    """Types of available workflows"""
    SMART_CAPTURE = "smart_capture"
    MOTION_ALERT = "motion_alert"
    SECURITY_SCAN = "security_scan"
    OBJECT_SEARCH = "object_search"
    AUTO_RECORD = "auto_record"
    SUMMARY_REPORT = "summary_report"


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Request/Response Models
# ============================================================================

class NaturalLanguageRequest(BaseModel):
    """Natural language command from OpenClaw AI"""
    query: str
    user_email: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    """Structured workflow execution request"""
    workflow_type: WorkflowType
    parameters: Dict[str, Any]
    user_email: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Workflow execution response"""
    workflow_id: str
    workflow_type: WorkflowType
    status: WorkflowStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


# ============================================================================
# AI Intent Parser
# ============================================================================

class IntentParser:
    """
    Parses natural language queries into structured workflow requests
    Uses simple pattern matching (can be enhanced with LLM later)
    """

    INTENT_PATTERNS = {
        # Smart Capture intents
        "smart_capture": [
            "capture", "take a picture", "snapshot", "grab frame",
            "what do you see", "show me camera"
        ],

        # Motion Alert intents
        "motion_alert": [
            "detect motion", "alert me when", "notify if",
            "watch for movement", "monitor activity"
        ],

        # Security Scan intents
        "security_scan": [
            "security check", "scan all cameras", "full sweep",
            "check perimeter", "security status"
        ],

        # Object Search intents
        "object_search": [
            "find", "search for", "locate", "when did you see",
            "show me all", "has there been", "any signs of"
        ],

        # Auto Record intents
        "auto_record": [
            "record", "start recording", "capture video",
            "record when", "save footage"
        ],

        # Summary Report intents
        "summary_report": [
            "summary", "report", "what happened", "activity log",
            "show me stats", "breakdown", "analysis"
        ]
    }

    CAMERA_PATTERNS = {
        "camera1": ["camera 1", "camera1", "136", "first camera", "front"],
        "camera2": ["camera 2", "camera2", "110", "second camera", "back"],
        "camera3": ["camera 3", "camera3", "106", "third camera", "side"],
        "all": ["all cameras", "every camera", "all", "everywhere"]
    }

    OBJECT_CLASSES = [
        "person", "people", "human",
        "car", "vehicle", "automobile",
        "dog", "cat", "pet", "animal",
        "bicycle", "bike",
        "truck", "bus"
    ]

    def parse(self, query: str) -> Optional[WorkflowRequest]:
        """Parse natural language query into workflow request"""
        query_lower = query.lower()

        # Detect workflow type
        workflow_type = self._detect_workflow_type(query_lower)
        if not workflow_type:
            return None

        # Extract parameters based on workflow type
        parameters = {}

        # Extract camera
        camera_id = self._extract_camera(query_lower)
        if camera_id:
            parameters["camera_id"] = camera_id

        # Extract object class
        object_class = self._extract_object_class(query_lower)
        if object_class:
            parameters["object_class"] = object_class

        # Extract time range
        time_range = self._extract_time_range(query_lower)
        if time_range:
            parameters.update(time_range)

        # Extract duration
        duration = self._extract_duration(query_lower)
        if duration:
            parameters["duration_seconds"] = duration

        # Workflow-specific parameters
        if workflow_type == WorkflowType.SMART_CAPTURE:
            parameters.setdefault("with_inference", True)
            parameters.setdefault("save_frame", True)

        elif workflow_type == WorkflowType.MOTION_ALERT:
            parameters.setdefault("threshold", 0.7)
            parameters.setdefault("continuous", True)

        elif workflow_type == WorkflowType.AUTO_RECORD:
            parameters.setdefault("duration_seconds", 60)
            parameters.setdefault("include_detections", True)

        elif workflow_type == WorkflowType.SUMMARY_REPORT:
            parameters.setdefault("hours", 24)

        return WorkflowRequest(
            workflow_type=workflow_type,
            parameters=parameters
        )

    def _detect_workflow_type(self, query: str) -> Optional[WorkflowType]:
        """Detect workflow type from query"""
        for workflow_type, patterns in self.INTENT_PATTERNS.items():
            if any(pattern in query for pattern in patterns):
                return WorkflowType(workflow_type)
        return None

    def _extract_camera(self, query: str) -> Optional[str]:
        """Extract camera ID from query"""
        for camera_id, patterns in self.CAMERA_PATTERNS.items():
            if any(pattern in query for pattern in patterns):
                return camera_id if camera_id != "all" else None
        return "camera1"  # Default

    def _extract_object_class(self, query: str) -> Optional[str]:
        """Extract object class from query"""
        for obj_class in self.OBJECT_CLASSES:
            if obj_class in query:
                return obj_class
        return None

    def _extract_time_range(self, query: str) -> Optional[Dict[str, float]]:
        """Extract time range from query"""
        now = time.time()

        # Last X hours
        if "last hour" in query or "past hour" in query:
            return {"start_time": now - 3600, "end_time": now}
        elif "last 24 hours" in query or "today" in query:
            return {"start_time": now - 86400, "end_time": now}
        elif "last week" in query:
            return {"start_time": now - 604800, "end_time": now}

        # This morning/afternoon/evening
        if "this morning" in query:
            start_of_day = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
            return {"start_time": start_of_day, "end_time": now}

        return None

    def _extract_duration(self, query: str) -> Optional[int]:
        """Extract duration in seconds from query"""
        import re

        # Look for patterns like "30 seconds", "5 minutes", "1 hour"
        patterns = [
            (r"(\d+)\s*seconds?", 1),
            (r"(\d+)\s*minutes?", 60),
            (r"(\d+)\s*hours?", 3600)
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, query)
            if match:
                return int(match.group(1)) * multiplier

        return None


# ============================================================================
# Workflow Executors
# ============================================================================

class WorkflowExecutor:
    """Executes workflow requests"""

    def __init__(self, video_api_base: str = "http://localhost:8888"):
        self.video_api = video_api_base
        self.intent_parser = IntentParser()

    async def execute_natural_language(self, request: NaturalLanguageRequest) -> WorkflowResponse:
        """Execute a natural language command"""
        # Parse intent
        workflow_request = self.intent_parser.parse(request.query)

        if not workflow_request:
            raise HTTPException(400, f"Could not understand query: {request.query}")

        # Add user context
        workflow_request.user_email = request.user_email

        # Execute workflow
        return await self.execute_workflow(workflow_request)

    async def execute_workflow(self, request: WorkflowRequest) -> WorkflowResponse:
        """Execute a structured workflow"""
        import uuid

        workflow_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # Route to appropriate workflow handler
            if request.workflow_type == WorkflowType.SMART_CAPTURE:
                result = await self._smart_capture(request.parameters)

            elif request.workflow_type == WorkflowType.MOTION_ALERT:
                result = await self._motion_alert(request.parameters)

            elif request.workflow_type == WorkflowType.SECURITY_SCAN:
                result = await self._security_scan(request.parameters)

            elif request.workflow_type == WorkflowType.OBJECT_SEARCH:
                result = await self._object_search(request.parameters)

            elif request.workflow_type == WorkflowType.AUTO_RECORD:
                result = await self._auto_record(request.parameters)

            elif request.workflow_type == WorkflowType.SUMMARY_REPORT:
                result = await self._summary_report(request.parameters)

            else:
                raise ValueError(f"Unknown workflow type: {request.workflow_type}")

            execution_time = (time.time() - start_time) * 1000

            return WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=request.workflow_type,
                status=WorkflowStatus.COMPLETED,
                result=result,
                execution_time_ms=execution_time
            )

        except Exception as e:
            return WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=request.workflow_type,
                status=WorkflowStatus.FAILED,
                error=str(e)
            )

    # ========================================================================
    # Workflow Implementations
    # ========================================================================

    async def _smart_capture(self, params: Dict) -> Dict:
        """
        Smart Capture Workflow
        - Captures frame from camera
        - Runs Hailo inference
        - Returns intelligent summary
        """
        import aiohttp

        camera_id = params.get("camera_id", "camera1")

        async with aiohttp.ClientSession() as session:
            # Capture frame with inference
            async with session.post(
                f"{self.video_api}/cameras/{camera_id}/capture",
                json={
                    "save_frame": params.get("save_frame", True),
                    "run_inference": params.get("with_inference", True)
                }
            ) as response:
                data = await response.json()

        # Generate natural language summary
        detections = data.get("detections", [])
        summary = self._generate_detection_summary(detections)

        return {
            "camera_id": camera_id,
            "timestamp": data["timestamp"],
            "summary": summary,
            "detections": detections,
            "frame": data.get("frame"),  # base64 image
            "file_path": data.get("file_path")
        }

    async def _motion_alert(self, params: Dict) -> Dict:
        """
        Motion Alert Workflow
        - Monitors camera for motion/detections
        - Sends alerts when threshold exceeded
        """
        import aiohttp

        camera_id = params.get("camera_id", "camera1")
        threshold = params.get("threshold", 0.7)
        duration = params.get("duration_seconds", 60)

        alerts = []
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration:
                # Capture and analyze frame
                async with session.post(
                    f"{self.video_api}/cameras/{camera_id}/capture",
                    json={"run_inference": True, "save_frame": False}
                ) as response:
                    data = await response.json()

                # Check for high-confidence detections
                detections = data.get("detections", [])
                high_confidence = [d for d in detections if d["confidence"] >= threshold]

                if high_confidence:
                    alerts.append({
                        "timestamp": data["timestamp"],
                        "detections": high_confidence,
                        "alert": f"Detected {len(high_confidence)} objects above {threshold:.0%} confidence"
                    })

                await asyncio.sleep(2)  # Check every 2 seconds

        return {
            "camera_id": camera_id,
            "duration_monitored": duration,
            "alerts": alerts,
            "total_alerts": len(alerts)
        }

    async def _security_scan(self, params: Dict) -> Dict:
        """
        Security Scan Workflow
        - Scans all cameras simultaneously
        - Detects potential security concerns
        """
        import aiohttp

        # Scan all cameras in parallel
        async with aiohttp.ClientSession() as session:
            # Get camera list
            async with session.get(f"{self.video_api}/cameras") as response:
                cameras_data = await response.json()

            cameras = cameras_data["cameras"]

            # Capture from all cameras
            tasks = []
            for camera in cameras:
                if camera["enabled"]:
                    task = session.post(
                        f"{self.video_api}/cameras/{camera['id']}/capture",
                        json={"run_inference": True, "save_frame": False}
                    )
                    tasks.append(task)

            responses = await asyncio.gather(*tasks)
            results = [await r.json() for r in responses]

        # Analyze for security concerns
        security_alerts = []
        camera_summaries = []

        for result in results:
            camera_id = result["camera_id"]
            detections = result.get("detections", [])

            # Flag potential security concerns
            concerns = []
            people_count = sum(1 for d in detections if d["class_name"] == "person")
            vehicle_count = sum(1 for d in detections if d["class_name"] in ["car", "truck", "motorcycle"])

            if people_count > 0:
                concerns.append(f"{people_count} person(s) detected")
            if vehicle_count > 0:
                concerns.append(f"{vehicle_count} vehicle(s) detected")

            camera_summaries.append({
                "camera_id": camera_id,
                "detections": detections,
                "concerns": concerns,
                "status": "alert" if concerns else "clear"
            })

            if concerns:
                security_alerts.append({
                    "camera_id": camera_id,
                    "concerns": concerns
                })

        return {
            "scan_timestamp": time.time(),
            "cameras_scanned": len(cameras),
            "security_status": "alert" if security_alerts else "all_clear",
            "alerts": security_alerts,
            "camera_details": camera_summaries
        }

    async def _object_search(self, params: Dict) -> Dict:
        """
        Object Search Workflow
        - Searches detection history for specific objects
        - Returns timeline and statistics
        """
        import aiohttp

        object_class = params.get("object_class")
        camera_id = params.get("camera_id")
        start_time = params.get("start_time")
        end_time = params.get("end_time")

        query = {
            "camera_id": camera_id,
            "class_name": object_class,
            "start_time": start_time,
            "end_time": end_time,
            "min_confidence": 0.5,
            "limit": 100
        }

        async with aiohttp.ClientSession() as session:
            # Query detections
            async with session.post(
                f"{self.video_api}/detections/query",
                json=query
            ) as response:
                detections_data = await response.json()

            # Get statistics
            stats_params = {}
            if camera_id:
                stats_params["camera_id"] = camera_id

            async with session.get(
                f"{self.video_api}/detections/stats",
                params=stats_params
            ) as response:
                stats_data = await response.json()

        detections = detections_data["detections"]

        # Generate timeline summary
        if detections:
            first_seen = min(d["timestamp"] for d in detections)
            last_seen = max(d["timestamp"] for d in detections)
            timeline = f"First seen at {datetime.fromtimestamp(first_seen).strftime('%H:%M:%S')}, " \
                      f"last seen at {datetime.fromtimestamp(last_seen).strftime('%H:%M:%S')}"
        else:
            timeline = "No detections found"

        return {
            "object_class": object_class,
            "camera_id": camera_id,
            "total_detections": len(detections),
            "timeline": timeline,
            "detections": detections[:10],  # Return first 10
            "statistics": stats_data
        }

    async def _auto_record(self, params: Dict) -> Dict:
        """
        Auto Record Workflow
        - Starts recording on specified camera
        - Optionally stops after duration
        """
        import aiohttp

        camera_id = params.get("camera_id", "camera1")
        duration = params.get("duration_seconds", 60)
        include_detections = params.get("include_detections", True)

        async with aiohttp.ClientSession() as session:
            # Start recording
            async with session.post(
                f"{self.video_api}/cameras/{camera_id}/record/start",
                json={
                    "duration_seconds": duration,
                    "include_detections": include_detections
                }
            ) as response:
                start_data = await response.json()

            recording_id = start_data["recording_id"]

            # Wait for recording to complete if duration specified
            if duration:
                await asyncio.sleep(duration + 2)  # Wait for recording to finish

                # Get recording details
                async with session.get(f"{self.video_api}/recordings") as response:
                    recordings_data = await response.json()

                recording = next(
                    (r for r in recordings_data["recordings"] if r["id"] == recording_id),
                    None
                )

                return {
                    "recording_id": recording_id,
                    "camera_id": camera_id,
                    "status": "completed",
                    "duration_seconds": duration,
                    "file_path": recording["file_path"] if recording else None,
                    "detection_count": recording["detection_count"] if recording else 0
                }

        return {
            "recording_id": recording_id,
            "camera_id": camera_id,
            "status": "recording",
            "duration_seconds": duration
        }

    async def _summary_report(self, params: Dict) -> Dict:
        """
        Summary Report Workflow
        - Generates comprehensive activity report
        - Includes statistics and highlights
        """
        import aiohttp

        camera_id = params.get("camera_id")
        hours = params.get("hours", 24)

        async with aiohttp.ClientSession() as session:
            # Get detection statistics
            stats_params = {"hours": hours}
            if camera_id:
                stats_params["camera_id"] = camera_id

            async with session.get(
                f"{self.video_api}/detections/stats",
                params=stats_params
            ) as response:
                stats_data = await response.json()

            # Get recent recordings
            recordings_params = {}
            if camera_id:
                recordings_params["camera_id"] = camera_id

            async with session.get(
                f"{self.video_api}/recordings",
                params=recordings_params
            ) as response:
                recordings_data = await response.json()

        # Generate natural language summary
        total = stats_data["total_detections"]
        top_classes = sorted(
            stats_data["class_counts"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        summary_text = f"In the last {hours} hours, detected {total} objects. "
        if top_classes:
            top_summary = ", ".join([f"{count} {cls}" for cls, count in top_classes])
            summary_text += f"Most common: {top_summary}."

        recordings = recordings_data["recordings"]
        recording_summary = f"Recorded {len(recordings)} videos with {sum(r['detection_count'] for r in recordings)} total detections."

        return {
            "time_window_hours": hours,
            "camera_id": camera_id,
            "summary": summary_text,
            "statistics": stats_data,
            "recordings": {
                "count": len(recordings),
                "total_detections": sum(r["detection_count"] for r in recordings),
                "recent": recordings[:5]
            },
            "recording_summary": recording_summary
        }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _generate_detection_summary(self, detections: List[Dict]) -> str:
        """Generate natural language summary of detections"""
        if not detections:
            return "No objects detected"

        # Count by class
        class_counts = {}
        for det in detections:
            class_name = det["class_name"]
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

        # Generate summary
        parts = []
        for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            if count == 1:
                parts.append(f"1 {class_name}")
            else:
                parts.append(f"{count} {class_name}s")

        if len(parts) == 1:
            return f"Detected {parts[0]}"
        elif len(parts) == 2:
            return f"Detected {parts[0]} and {parts[1]}"
        else:
            return f"Detected {', '.join(parts[:-1])}, and {parts[-1]}"


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Video Skill Agent Workflows",
    description="AI-powered workflows for natural language video control",
    version="1.0.0"
)

executor = WorkflowExecutor()


@app.post("/agent/query", response_model=WorkflowResponse)
async def process_natural_language(request: NaturalLanguageRequest):
    """
    Process a natural language query from OpenClaw AI

    Examples:
    - "Show me camera 1"
    - "Has anyone been detected in the last hour?"
    - "Record camera 2 for 5 minutes"
    - "Give me a security summary"
    """
    return await executor.execute_natural_language(request)


@app.post("/agent/workflow", response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowRequest):
    """Execute a structured workflow"""
    return await executor.execute_workflow(request)


@app.get("/agent/workflows")
async def list_workflows():
    """List all available workflows"""
    return {
        "workflows": [
            {
                "type": "smart_capture",
                "name": "Smart Capture",
                "description": "Capture frame with AI analysis",
                "examples": [
                    "Show me camera 1",
                    "What do you see on camera 2?",
                    "Take a picture of the front door"
                ]
            },
            {
                "type": "motion_alert",
                "name": "Motion Alert",
                "description": "Monitor for motion and send alerts",
                "examples": [
                    "Alert me if someone appears",
                    "Watch camera 3 for movement",
                    "Notify if you detect a person"
                ]
            },
            {
                "type": "security_scan",
                "name": "Security Scan",
                "description": "Scan all cameras for security concerns",
                "examples": [
                    "Do a security check",
                    "Scan all cameras",
                    "What's the security status?"
                ]
            },
            {
                "type": "object_search",
                "name": "Object Search",
                "description": "Search detection history for objects",
                "examples": [
                    "Find all people detected today",
                    "When was a car last seen?",
                    "Show me dog detections"
                ]
            },
            {
                "type": "auto_record",
                "name": "Auto Record",
                "description": "Start recording with automatic stop",
                "examples": [
                    "Record camera 1 for 5 minutes",
                    "Start recording the back door",
                    "Capture video for 30 seconds"
                ]
            },
            {
                "type": "summary_report",
                "name": "Summary Report",
                "description": "Generate activity report",
                "examples": [
                    "Give me a summary",
                    "What happened today?",
                    "Show me activity stats"
                ]
            }
        ]
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "agent_workflows"}


if __name__ == "__main__":
    import uvicorn
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8889

    print(f"Starting Agent Workflows Service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
