import uvicorn
from config_logs import dict_config


if __name__ == "__main__":

    uvicorn.run("application.routes:app", host="0.0.0.0",
                                                port=8000,
                                                reload=True,
                                                log_config=dict_config
                                                )
