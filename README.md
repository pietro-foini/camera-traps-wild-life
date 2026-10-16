# Camera-Traps-Wild-Life

[![GitHub Release](https://img.shields.io/github/v/tag/pietro-foini/camera-traps-wild-life?label=version)](https://github.com/pietro-foini/camera-traps-wild-life/releases)
[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen.svg)](https://app-camera-traps-wildlife-latest.onrender.com/)

Hello there! 😀

This project was born from the idea of applying such algorithms to camera traps located on my family’s property in a 
remote area of Italy, where wildlife is frequently observed. The goal was to develop a simple application for fixed 
camera trap systems, where a basic motion detection algorithm could automatically identify subjects to be analyzed 
by a fine-tuned machine learning model for image classification.

Example of results applied to generic camera traps (used only for inference purposes):

<table width="100%" align="center">
  <tr>
    <td align="center" width="33%">
      <video src="https://github.com/user-attachments/assets/f903c4a7-a3cb-48b9-8807-4d2c9d73d5d4" width="100%" muted autoplay loop></video>
    </td>
    <td align="center" width="33%">
      <video src="https://github.com/user-attachments/assets/4f40051a-4307-4f2d-987a-77a2167c8220" width="100%" muted autoplay loop></video>
    </td>
    <td align="center" width="33%">
      <video src="https://github.com/user-attachments/assets/7968e2a3-fbf9-4bf2-966d-ab31f4e82518" width="100%" muted autoplay loop></video>
    </td>
  </tr>
</table>

Using Grad-CAM, we achieve model explainability to observe where the model focuses to reach its conclusions:

<p align="center">
  <img src="assets/gradcam_badger.jpg" alt="Grad-CAM Visualization" width="232">
  <img src="assets/gradcam_hare.jpg" alt="Grad-CAM Visualization" width="232">
  <img src="assets/gradcam_fox.jpg" alt="Grad-CAM Visualization" width="232">
</p>

<p align="center">
  <em>These images were retrieved from the <a href="https://emammal.si.edu/">eMammals</a> website in reference to the Tierschnappschuss Project based on camera trap locations in Italy.</em>
</p>

## Getting Started

You can run this project locally either using **Docker Compose** (for a quick containerized setup) or through a 
**Manual Setup** directly on your host machine.

### Prerequisites

1. Before starting the application in both scenarios, download the required pre-trained model weights from the 
   [GitHub Releases](https://github.com/pietro-foini/Camera-traps-wild-life/releases) page of this repository:
   
   - **Object Detection:** MegaDetector v1000 model weights.
   - **Classification:** Fine-tuned ConvNeXtBase model weights.

   You can store these files anywhere on your machine; we will refer to this directory as `/path/to/your/local/models` 
   in the following steps.

2. Create an environment file anywhere on your machine; we will refer to this file as `/path/to/your/local/env`. At this 
   point we can start adding the paths to the previously downloaded models. Example:

    ```
    CLASSIFIER_MODEL_PATH=/path/to/your/local/models/classifier.tflite
    DETECTOR_MODEL_PATH=/path/to/your/local/models/detector.tflite
    ```

### Manual Setup

Follow these steps if you want to set up the development environment, external services, and dependencies natively on 
your system without Docker.

#### Python Dependencies

This project requires Python 3.11 or 3.12 and relies on Poetry for dependency management. The project is structured to 
support three distinct installation modes depending on your hardware and requirements.

##### Lite Setup

This setup is designed for edge deployments or lightweight servers where inference is handled exclusively via TensorFlow 
Lite models, resulting in a significantly smaller storage footprint.

```bash
poetry install --only main
```

##### GPU Setup

This setup is designed for development, training, or production inference on machines equipped with NVIDIA GPUs.

```bash
poetry install --extras gpu
```

##### CPU Setup

Because pip and Poetry do not natively allow conditional hardware-based resolution in a single configuration block, 
the CPU and GPU dependencies are mutually exclusive. You must manually modify the `pyproject.toml` file to switch from GPU to CPU.

After changing `pyproject.toml`, regenerate the lock file:

```bash
poetry lock
```

Finally, install the CPU dependencies with:

```bash
poetry install --extras cpu
```

#### Database

Make sure to have a running PostgreSQL instance (https://www.postgresql.org/download/), which will have you create a 
default `postgres` user with its password.

Using any graphical client (e.g. DBeaver) for the local configuration, create a connection to PostgreSQL on port
5432 and create a database:

```sql
CREATE DATABASE cameratraps;
```

At the end of this step, add to the environment file the variables referring to the database.

Example:

```
DB_USER=postgres
DB_PASSWORD=xxxxxxxx
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cameratraps
```

#### Storage

Object storage is provided by [SeaweedFS](https://github.com/seaweedfs/seaweedfs), which exposes an S3-compatible API and runs as a single executable.

- Download the release for your operating system from the
  [official releases page](https://github.com/seaweedfs/seaweedfs/releases) and extract the `weed` executable into a folder of your choice.
- Add that folder to your system `PATH`.
- Create a directory where the data will be stored (e.g. `./seaweedfs-data`).

   ```bash
   mkdir ./seaweedfs-data
   ```

- Start SeaweedFS with the S3 module enabled:

   ```bash
     weed server -s3 -dir="./seaweedfs-data"
   ```

  (Keep this terminal window running as long as you need the storage active.)

Once started, the following services are available:

- **Filer (file browser)**: http://localhost:8888, where you can browse, download and view the stored objects
  (buckets are under `/buckets`).
- **Master (cluster status)**: http://localhost:9333, to check volumes and disk space.
- **S3 API**: http://localhost:8333.

At the end of this step, add to the environment file the variables referring to the storage.

Example:

```
S3_ENDPOINT_URL=http://localhost:8333
S3_ACCESS_KEY=xxxxxxxx
S3_SECRET_KEY=xxxxxxxx
```

#### Running the Application

With **PostgreSQL** and **SeaweedFS** running in the background, start the application server:

   ```bash
   uvicorn camera_traps.main:app --env-file /path/to/your/local/env --reload
   ```

The Application will be available at http://localhost:8000.
  
### Docker Setup

If you prefer running the entire stack (Application, PostgreSQL, and SeaweedFS) in containers, configure your 
`/path/to/your/local/env` file with the internal container paths for the models (since Docker mounts the models directory 
to `/app/models`):

```
CLASSIFIER_MODEL_PATH=/app/models/classifier.tflite
DETECTOR_MODEL_PATH=/app/models/detector.tflite
DB_USER=postgres
DB_PASSWORD=password
DB_PORT=5432
DB_NAME=camera_traps
S3_ACCESS_KEY=xxxxxxxx
S3_SECRET_KEY=xxxxxxxx
```

(Note: `DB_HOST` and `S3_ENDPOINT_URL` are automatically set inside `docker-compose.yml`).

Run the entire pipeline with a single command:

```bash
ENV_FILE=/path/to/your/local/env MODELS_DIR=/path/to/your/local/models docker compose --env-file /path/to/your/local/env up --build
```

Note on defaults: If your environment file is named .env in the project root and your models are stored in ./models, 
you can simply run:

```bash
docker compose up --build
```

Once the containers are running:

- The Application will be available at http://localhost:8000.
- SeaweedFS Filer will be available at http://localhost:8888.

## How It Works 

The entire infrastructure is designed around an **event-driven pipeline**: whenever a new video (or image, if you modify 
the configuration) is uploaded to the `input/` folder inside the target  bucket, SeaweedFS automatically triggers the inference 
pipeline by sending an HTTP `POST` notification to the application's `/predict-video` endpoint.

This mechanism is enabled through the [`notification.toml`](./notification.toml) file located in the project root. For 
more information on how SeaweedFS handles event notifications, refer to the official 
[Filer Notification Webhook documentation](https://github.com/seaweedfs/seaweedfs/wiki/Filer-Notification-Webhook).

Note: In the Docker Setup, the `notification.toml` file is automatically mounted into the storage container, and the 
webhook endpoint is dynamically overridden to http://app:8000/predict-video via `docker-compose.yaml`.

The processed videos (or images) will be automatically uploaded to the `output/` folder inside the target bucket and
to the corresponding PostgreSQL tables.

-----

## Model

The inference pipeline consists of three stages:

- **Object Detection:** `MegaDetector` is employed to detect animals, humans, and vehicles in camera trap images, filtering out empty frames or background noise.
- **Classification:** Detected cropped regions are processed by a fine-tuned `ConvNeXtBase` model trained to identify specific wildlife species.
- **Tracking:** Uses a `SORTTracker` to maintain object identities across video frames and applies label smoothing to stabilize predictions along tracked trajectories.

Training and fine-tuning were executed on an NVIDIA GeForce RTX 5060 Laptop GPU.

## Dataset

The current dataset was assembled by combining multiple online data sources to gather camera trap images captured in both 
daytime and nighttime settings. Subsequently, all images were manually reviewed to filter out noisy, misleading, or 
poorly identifiable samples, ensuring higher dataset quality. The data was collected over several years; therefore, we 
cannot guarantee that the provided links remain active or publicly accessible.

Images smaller than $100 \times 100$ pixels are filtered out to prevent low-quality samples from degrading model performance. 
After filtering, the final dataset consists of approximately 74,227 images distributed across day and night captures:

| label             | setting | count |
|-------------------|---------|-------|
| None_of_the_above | day     | 3798  |
| None_of_the_above | night   | 637   |
| badger            | day     | 870   |
| badger            | night   | 1353  |
| bear              | day     | 3308  |
| bear              | night   | 1311  |
| bird              | day     | 1853  |
| bird              | night   | 464   |
| boar              | day     | 3460  |
| boar              | night   | 2395  |
| cat               | day     | 2970  |
| cat               | night   | 4653  |
| cow               | day     | 4162  |
| cow               | night   | 590   |
| deer              | day     | 5180  |
| deer              | night   | 3545  |
| dog               | day     | 7285  |
| dog               | night   | 957   |
| fox               | day     | 1200  |
| fox               | night   | 2121  |
| hare              | day     | 1722  |
| hare              | night   | 2724  |
| human             | day     | 4671  |
| human             | night   | 161   |
| squirrel          | day     | 2570  |
| squirrel          | night   | 127   |
| vehicle           | day     | 2592  |
| vehicle           | night   | 47    |
| weasel            | day     | 2731  |
| weasel            | night   | 1634  |
| wolf              | day     | 1768  |
| wolf              | night   | 1368  |

The dataset folder structure is then organized as follows:

    root
     └── dataset
          ├── label1
          │   ├─ image1.jpg
          │   ├─ image2.png                              
          │   └─ ...
          └── label2
              └── ...

The filename of each image is defined as follows:

    {referenceNameDataset}_{nameLabel}_{timeCondition}_{progressiveIndex}.jpg

List of sources:

- NTLNP: https://paperswithcode.com/dataset/ntlnp-wildlife-image-dataset
- CCT20: https://lila.science/datasets/caltech-camera-traps
- Sheffield: https://figshare.shef.ac.uk/articles/dataset/Badger_datasets_for_image_recognition/8182370/1
- ENA24: https://lila.science/datasets/ena24detection
- LilaMissouri: https://lila.science/datasets/missouricameratraps
- WCS: https://lila.science/datasets/wcscameratraps
- PennFudan: https://www.cis.upenn.edu/~jshi/ped_html/
- yybbdog: https://www.lirmm.fr/YT-BB-Dog_Sibetan/
- nz: https://lila.science/datasets/nz-trailcams
- idaho: https://lila.science/datasets/idaho-camera-traps/
- felidae: https://lila.science/datasets/felidae-conservation-fund
- island: https://lila.science/datasets/channel-islands-camera-traps/
- seattleish: https://lila.science/datasets/seattleish-camera-traps/
- nkhotakota: https://lila.science/datasets/nkhotakota-camera-traps/
- roboflow: https://roboflow.com/
- oregon: https://lila.science/datasets/oregon-critters/
- maasai: https://lila.science/datasets/biome-health-project-maasai-mara
- UKCEH: https://catalogue.ceh.ac.uk/documents/bf82cec2-5f8a-407c-bf74-f8689ca35e83
- MOF: https://github.com/umr-ds/Mammal-Bird-Camera-Trap-Recognition/blob/main/data/data_download.sh
- BNP: https://github.com/umr-ds/Mammal-Bird-Camera-Trap-Recognition/blob/main/data/data_download.sh

## License

MIT

## Contacts

If you would like to request access to the pre-trained model weights, the curated dataset, or if you have any questions 
regarding the project, feel free to get in touch.

Email: pietro.foini1@gmail.com
