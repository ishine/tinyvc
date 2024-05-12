import argparse
import os
import glob

import torch
import torch.nn.functional as F
import torchaudio
from torchaudio.functional import resample

from tqdm import tqdm

from module.encoder import Encoder
from module.decoder import Decoder
from module.convertor import Convertor
from module.common import estimate_energy


parser = argparse.ArgumentParser()
parser.add_argument('-i', '--inputs', default="./inputs/")
parser.add_argument('-o', '--outputs', default="./outputs/")
parser.add_argument('-encp', '--encoder-path', default='./models/encoder.pt')
parser.add_argument('-decp', '--decoder-path', default='./models/decoder.pt')
parser.add_argument('-f0-est', '--f0-estimation', default='default')
parser.add_argument('-idx', '--index', default='NONE')
parser.add_argument('-t', '--target', default='target.wav')
parser.add_argument('-d', '--device', default='cpu')
parser.add_argument('-p', '--pitch-shift', default=0.0, type=float)
parser.add_argument('-c', '--chunk-size', default=1920, type=int)
parser.add_argument('-b', '--buffer-size', default=4, type=int)
parser.add_argument('-nc', '--no-chunking', default=False, type=bool)

args = parser.parse_args()

device = torch.device(args.device)
encoder = Encoder().to(device).eval()
encoder.load_state_dict(torch.load(args.encoder_path, map_location=device))
decoder = Decoder().to(device).eval()
decoder.load_state_dict(torch.load(args.decoder_path, map_location=device))
convertor = Convertor(encoder, decoder).to(device)

chunk_size = args.chunk_size
buffer_size = args.buffer_size * chunk_size

# load target
if args.index == 'NONE':
    wf, sr = torchaudio.load(args.target)
    wf = resample(wf, sr, 24000).to(device)
    tgt = convertor.encode_target(wf)
else:
    tgt = torch.load(args.index).to(device)

if not os.path.exists(args.outputs):
    os.mkdir(args.outputs)

paths = []
support_formats = ['wav', 'ogg', 'mp3']

for fmt in support_formats:
    paths += glob.glob(os.path.join(args.inputs, "*." + fmt))

for i, path in enumerate(paths):
    print(f"Converting {path} ...")
    wf, sr = torchaudio.load(path)
    wf = resample(wf, sr, 24000)
    wf = wf.mean(dim=0, keepdim=True)
    
    wf = convertor.convert(wf, tgt, args.pitch_shift, args.device, args.f0_estimation, args.chunk_size, args.buffer_size * args.chunk_size, args.no_chunking)

    file_name = f"{os.path.splitext(os.path.basename(path))[0]}"
    torchaudio.save(os.path.join(args.outputs, f"{file_name}.wav"), src=wf, sample_rate=24000)
