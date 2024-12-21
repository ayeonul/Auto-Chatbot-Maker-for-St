import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer
from tqdm.auto import tqdm

class Encoder(object):
    def __init__(self, model_name='BM-K/KoSimCSE-roberta-multitask', device='cuda', pooling_method='cls'):
        '''
        JIT compile with TorchScript.
        '''
        assert device in ['cuda', 'cpu']
        assert pooling_method in ['cls', 'mean']
        self.device = device
        self.pooling = pooling_method

        tokenizer = AutoTokenizer.from_pretrained(model_name, torchscript=True)
        model = AutoModel.from_pretrained(model_name, torchscript=True)
        model.to(device)
        model.eval()
        
        sample_tokens = tokenizer(['안녕하세요.', '한글 테스트용 샘플 토큰 입력 입니다.'], padding=True, truncation=True, return_tensors='pt').to(device)
        input_ids = sample_tokens['input_ids']
        attn_msk = sample_tokens['attention_mask']
        type_ids = sample_tokens['token_type_ids']
        
        self.tokenizer = tokenizer
        model = torch.jit.trace(model, (input_ids, attn_msk, type_ids))
        self.model = torch.jit.freeze(model)

    @staticmethod
    def mean_pooling(model_output, attention_mask):
        '''
        Mean Pooling - Take attention mask into account for correct averaging.
        From https://huggingface.co/snunlp/KR-SBERT-V40K-klueNLI-augSTS
        '''
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def encode(self, sentences, batch_size=128, prog_bar=False):
        res = []
        length = len(sentences)
        if prog_bar:
            pbar = tqdm(total=length)
        for idx in range(0, length, batch_size):
            next_idx = min(idx + batch_size, length)
            sentences_input = sentences[idx:next_idx]

            encoded_input = self.tokenizer(sentences_input, padding=True, truncation=True, return_tensors='pt').to(self.device)
            input_ids = encoded_input['input_ids']
            attn_msk = encoded_input['attention_mask']
            type_ids = encoded_input['token_type_ids']

            with torch.no_grad():
                model_output, _ = self.model(input_ids, attn_msk, type_ids)
                
            if self.pooling == 'cls':
                sentence_embeddings = model_output[:,0]
            elif self.pooling == 'mean':
                sentence_embeddings = self.mean_pooling(model_output, attn_msk)
            else:
                raise

            res.append(sentence_embeddings.cpu().numpy())
            
            if prog_bar:
                pbar.update(n=next_idx - idx)
        return np.concatenate(res)

    __call__ = encode