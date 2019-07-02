from concurrent.futures import ProcessPoolExecutor
from functools import partial
import numpy as np
import os
import pickle
from util import audio
from datasets import all_txt


def build_from_path(in_dir, out_dir, num_workers=1, tqdm=lambda x: x):
  '''Preprocesses the LJ Speech dataset from a given input path into a given output directory.

    Args:
      in_dir: The directory where you have downloaded the LJ Speech dataset
      out_dir: The directory to write the output into
      num_workers: Optional number of worker processes to parallelize across
      tqdm: You can optionally pass tqdm to get a nice progress bar

    Returns:
      A list of tuples describing the training examples. This should be written to train.txt
  '''
  # We use ProcessPoolExecutor to parallize across processes. This is just an optimization and you
  # can omit it and just call _process_utterance on each input if you want.
  executor = ProcessPoolExecutor(max_workers=num_workers)
  futures = []
  index = 1
  in_dir = os.path.join(in_dir,'Wav')
  paths = []
  for i,(root, dirs, files) in enumerate(os.walk(in_dir, topdown=True)):
    for f in files:
      paths.append(os.path.join(root,f))

  df_all_txt = all_txt.read_all_txt()
  for p in paths[:]:
    fname = os.path.basename(p)
    name = int( fname.split('.')[0])
    row = df_all_txt.loc[name]
    text = row.script
    label = row.emotion_label

    futures.append(executor.submit(partial(_process_utterance, out_dir, index, fname, p, text, label)))
    index += 1
  return [future.result() for future in tqdm(futures)]


def _process_utterance(out_dir, index, fname, wav_path, text, label):
  '''Preprocesses a single utterance audio/text pair.

  This writes the mel and linear scale spectrograms to disk and returns a tuple to write
  to the train.txt file.

  Args:
    out_dir: The directory to write the spectrograms into
    index: The numeric index to use in the spectrogram filenames.
    wav_path: Path to the audio file containing the speech input
    text: The text spoken in the input audio file

  Returns:
    A (spectrogram_filename, mel_filename, n_frames, text) tuple to write to train.txt
  '''

  # Load the audio to a numpy array:
  wav = audio.load_wav(wav_path)

  # Compute the linear-scale spectrogram from the wav:
  spectrogram = audio.spectrogram(wav).astype(np.float32)
  n_frames = spectrogram.shape[1]

  # Compute a mel-scale spectrogram from the wav:
  mel_spectrogram = audio.melspectrogram(wav).astype(np.float32)

  # Write the spectrograms to disk:
  spectrogram_filename = 'emotion-spec-%05d.npy' % index
  mel_filename = 'emtion-mel-%05d.npy' % index
  np.save(os.path.join(out_dir, spectrogram_filename), spectrogram.T, allow_pickle=False)
  np.save(os.path.join(out_dir, mel_filename), mel_spectrogram.T, allow_pickle=False)

  # Return a tuple describing this training example:
  return (fname, spectrogram_filename, mel_filename, n_frames, text, label)
