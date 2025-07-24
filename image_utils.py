import os, time, random, logging, requests
from g4f import Client
from PIL import Image, ImageDraw

log = logging.getLogger("image_utils")
REQUESTS_TIMEOUT = 120
client = Client()

def save_image_from_url(url: str, prompt: str, image_num: int, folder_path: str, model: str, index: int) -> str:
    try:
        r = requests.get(url, timeout=REQUESTS_TIMEOUT); r.raise_for_status()
        fname = f"img_{index}_{model}_{image_num}.png"
        path = os.path.join(folder_path, fname)
        with open(path, "wb") as f: f.write(r.content)
        log.info(f"Image downloaded and saved to {path}")
        return path
    except Exception as e:
        log.error(f"Error downloading image: {e}")
        dummy = Image.new("RGB",(512,512),"white"); draw=ImageDraw.Draw(dummy)
        draw.text((256,256), f"Failed: {prompt[:50]}", fill="black", anchor="mm")
        df = os.path.join(folder_path, f"dummy_{model}_{index}_{image_num}.png")
        os.makedirs(folder_path,exist_ok=True); dummy.save(df)
        return df

def generate_image_g4f(prompt: str, index: int, folder_path: str, model: str, image_num: int, width: int, height: int, task_id: str=None) -> str:
    start=time.time()
    if model.lower()=="midjourney" and "--ar" not in prompt: prompt+=" --ar 16:9"
    try:
        resp = client.images.generate(model=model,prompt=prompt,response_format="url",
                                      width=width,height=height,timeout=REQUESTS_TIMEOUT)
        url = resp.data[0].url
        os.makedirs(folder_path,exist_ok=True)
        save_image_from_url(url,prompt,image_num,folder_path,model,index)
        log.info(f"Image saved in {time.time()-start:.1f}s")
        return os.path.join(folder_path, f"{task_id or 'img'}_{index}_{model}_{image_num}.png")
    except Exception as e:
        log.error(f"generate_image_g4f failed: {e}")
        dummy = Image.new("RGB",(width,height),"white"); draw=ImageDraw.Draw(dummy)
        draw.text((width//2,height//2), prompt[:50], fill="black", anchor="mm")
        fn = os.path.join(folder_path, f"dummy_{model}_{index}_{image_num}.png")
        dummy.save(fn); return fn

def generate_images_for_prompt(prompt:str,index:int,folder_path:str,model:str,num_images:int,width:int,height:int,task_id=None)->list[str]:
    images=[]
    g4f_models=["dall-e-3","midjourney","flux","sdxl","sdxl-lora","sd-3","playground-v2.5","flux-pro","flux-dev","flux-realism","flux-anime","flux-3d","flux-4o","any-dark"]
    use_g4f = model in g4f_models and callable(globals().get("generate_image_g4f"))
    try:
        if use_g4f:
            for i in range(num_images):
                images.append(generate_image_g4f(prompt,index,folder_path,model,i+1,width,height,task_id))
        else:
            for i in range(num_images):
                seed=random.randint(1,10**6)
                image=client.text_to_image(prompt=prompt,model=model,height=height,width=width,seed=seed)
                os.makedirs(folder_path,exist_ok=True)
                fn=os.path.join(folder_path, f"personality_{index}_{model}_{i+1}.jpeg")
                image.save(fn,format="JPEG"); images.append(fn)
        return images
    except Exception as e:
        log.error(f"Error generating images: {e}")
        return images
