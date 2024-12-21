import pandas as pd, numpy as np



class Search:
    def __init__(self, target_embs:pd.DataFrame, res_cols:pd.DataFrame) -> None:
        assert len(target_embs.columns) == 1, "embedding df는 컬럼 하나만!!!!!!!!!!!!!!!!!"

        self.target_embs = target_embs
        self.res_cols = res_cols

    @staticmethod
    def scoring(emb1, emb2, normalize:bool):
        if normalize:
            emb1 = emb1 / np.linalg.norm(emb1, axis=1, keepdims=True)
            emb2 = emb2 / np.linalg.norm(emb2, axis=1, keepdims=True)

        score = emb1 @ emb2.T
        return score[0][0]

    def search(self, query_emb, n=5, normalize=True):
        score_df = self.target_embs.copy()
        score_df['score'] = score_df[score_df.columns[0]].apply(self.scoring, args=(query_emb, normalize))

        score_df = pd.concat([score_df, self.res_cols], axis=1)
        search_res = score_df.sort_values('score', ascending=False).head(n)
        cols = list(self.res_cols.columns)
        res = search_res[cols + ['score']]

        return res