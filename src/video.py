from moviepy.editor import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip
from moviepy.video.fx.all import crop
from typing import List, Tuple
from termcolor import colored
import os


def create_video_from_media(media_paths: List[str], audio_path: str, output_path: str, threads: int, target_size: Tuple[int, int]):
    """
    Crea un vídeo a partir de una lista de imágenes y/o vídeos y un fichero de audio,
    usando una resolución de destino específica. Los vídeos se usarán sin su audio original
    y se adaptarán a la duración necesaria.
    """
    print(colored("[+] Creando vídeo a partir de imágenes...", "blue"))

    try:
        audio_clip = AudioFileClip(audio_path)
        total_audio_duration = audio_clip.duration

        if not media_paths:
            raise ValueError("La lista de medios (imágenes/vídeos) no puede estar vacía.")

        # Separar imágenes y vídeos y calcular la duración total de los vídeos
        image_paths_list = []
        video_clips_to_process = []
        total_video_duration = 0

        for media_path in media_paths:
            file_extension = os.path.splitext(media_path)[1].lower()
            if file_extension in ['.jpg', '.jpeg', '.png']:
                image_paths_list.append(media_path)
            elif file_extension in ['.mp4', '.mov', '.avi']:
                # Cargar el clip de vídeo para obtener su duración
                video_clip = VideoFileClip(media_path)
                total_video_duration += video_clip.duration
                video_clips_to_process.append((media_path, video_clip))
            else:
                print(colored(f"[!] Formato no soportado, omitiendo: {media_path}", "yellow"))

        # Calcular la duración para cada imagen
        remaining_duration_for_images = total_audio_duration - total_video_duration
        duration_per_image = 0

        if remaining_duration_for_images > 0 and image_paths_list:
            duration_per_image = remaining_duration_for_images / len(image_paths_list)
            print(colored(f"[+] Duración calculada por imagen: {duration_per_image:.2f}s","magenta"))
        elif remaining_duration_for_images < 0:
            print(colored("[!] Aviso: La duración de los vídeos subidos excede la del audio. Se ignorarán las imágenes y el vídeo se recortará.","yellow"))

        # Paso 3: Crear los clips finales con las duraciones correctas
        final_clips = []
        video_clips_map = {path: clip for path, clip in video_clips_to_process}

        print(colored(f"[+] Creando vídeo en resolución: {target_size[0]}x{target_size[1]}", "magenta"))

        for media_path in media_paths:
            # Identificar si es imagen o vídeo por la extensión del fichero
            clip = None
            file_extension = os.path.splitext(media_path)[1].lower()

            if file_extension in ['.jpg', '.jpeg', '.png']:
                if duration_per_image > 0:  # Solo añade imágenes si hay tiempo para ellas
                    clip = ImageClip(media_path).set_duration(duration_per_image)
            elif file_extension in ['.mp4', '.mov', '.avi']:
                # Usar el clip ya cargado
                video_clip = video_clips_map.get(media_path)
                if video_clip:
                    clip = video_clip.without_audio()

            if clip:
                # Redimensionado y recorte unificado para todos los clips
                if (clip.w / clip.h) < (target_size[0] / target_size[1]):
                    clip = clip.resize(width=target_size[0])
                else:
                    clip = clip.resize(height=target_size[1])

                clip = crop(clip, x_center=clip.w / 2, y_center=clip.h / 2, width=target_size[0], height=target_size[1])
                clip = clip.set_fps(24)
                final_clips.append(clip)

        if not final_clips:
            raise ValueError("No se pudieron procesar los medios. El vídeo final estaría vacío.")

        # Concatenar, añadir audio y exportar
        final_video = concatenate_videoclips(final_clips, method="compose")
        final_video = final_video.set_audio(audio_clip)

        # Asegurar que la duración final del vídeo coincida exactamente con la del audio
        final_video = final_video.set_duration(total_audio_duration)

        final_video.write_videofile(output_path, threads=threads, codec="libx264", logger='bar')

        # Limpiar los clips de vídeo de la memoria
        for _, clip in video_clips_to_process:
            clip.close()

        print(colored(f"[+] Vídeo generado con éxito en: {output_path}", "green"))
        return output_path

    except Exception as e:
        print(colored(f"[-] Error al crear el vídeo: {e}", "red"))
        raise
