from fastapi import FastAPI, Response
from pydantic import BaseModel
import datetime
import random

app = FastAPI(title="Streamo Mock API")

# Global state to simulate failures
state = {
    "fail_mode": False,
    "fail_code": 429
}

class WeatherData(BaseModel):
    id: int
    timestamp: str
    temperature: float
    humidity: int

from fastapi.responses import JSONResponse

@app.get("/data", response_model=WeatherData)
def get_data(response: Response):
    if state["fail_mode"]:
        headers = {}
        if state["fail_code"] == 429:
            headers["Retry-After"] = "2"
        return JSONResponse(status_code=state["fail_code"], content={"detail": f"Simulated failure: {state['fail_code']}"}, headers=headers)
        
    return WeatherData(
        id=random.randint(1000, 9999),
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        temperature=round(random.uniform(10.0, 35.0), 1),
        humidity=random.randint(40, 90)
    )

@app.post("/fail")
def toggle_fail(enabled: bool = True, code: int = 429):
    state["fail_mode"] = enabled
    state["fail_code"] = code
    return {"message": f"Fail mode set to {enabled} with code {code}"}
