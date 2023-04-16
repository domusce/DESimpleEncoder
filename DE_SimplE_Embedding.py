import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from bisect import bisect_left

import encoder
import random
import tqdm

class DE_SimplE(nn.Module):
    def __init__(self, data, ent_encoder, rel_encoder, numEnt, s_emb_dim, t_emb_dim, dimenson=300, dropout=0.1):
        super(DE_SimplE).__init__()

        self.data = data
        self.numEnt = numEnt
        self.dropout = dropout
        self.dimenson = dimenson
        self.s_emb_dim = s_emb_dim
        self.t_emb_dim = t_emb_dim
        self.ent_encoder = ent_encoder
        self.rel_encoder = rel_encoder
        self.rel_encoder_i = rel_encoder
        self.time_nl = torch.sin

        # nn.init.xavier_uniform(self.ent_encoder.weight)

    
    def create_time_embedds(self):
        
        # frequency embeddings for the entities
        self.m_freq_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.m_freq_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        
        self.d_freq_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.d_freq_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()

        self.y_freq_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.y_freq_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()

        # phi embeddings for the entities 
        self.m_phi_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.m_phi_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        
        self.d_phi_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.d_phi_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()

        self.y_phi_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.y_phi_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()

        # amps embeddings for the entities
        self.m_amps_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.m_amps_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        
        self.d_amps_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.d_amps_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()

        self.y_amps_h = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()
        self.y_amps_t = nn.Embedding(self.numEnt, self.t_emb_dim).cuda()


        nn.init.xavier_uniform_(self.m_freq_h.weight)
        nn.init.xavier_uniform_(self.d_freq_h.weight)
        nn.init.xavier_uniform_(self.y_freq_h.weight)
        nn.init.xavier_uniform_(self.m_freq_t.weight)
        nn.init.xavier_uniform_(self.d_freq_t.weight)
        nn.init.xavier_uniform_(self.y_freq_t.weight)

        nn.init.xavier_uniform_(self.m_phi_h.weight)
        nn.init.xavier_uniform_(self.d_phi_h.weight)
        nn.init.xavier_uniform_(self.y_phi_h.weight)
        nn.init.xavier_uniform_(self.m_phi_t.weight)
        nn.init.xavier_uniform_(self.d_phi_t.weight)
        nn.init.xavier_uniform_(self.y_phi_t.weight)

        nn.init.xavier_uniform_(self.m_amps_h.weight)
        nn.init.xavier_uniform_(self.d_amps_h.weight)
        nn.init.xavier_uniform_(self.y_amps_h.weight)
        nn.init.xavier_uniform_(self.m_amps_t.weight)
        nn.init.xavier_uniform_(self.d_amps_t.weight)
        nn.init.xavier_uniform_(self.y_amps_t.weight)

    def get_time_embeddings(self, entities, days, months, years, h_or_t):
        if h_or_t == 'head':
            emb = self.y_amps_h(entities)*self.time_nl(self.y_freq_h(entities)*years + self.y_phi_h(entities))
            emb += self.m_amps_h(entities)*self.time_nl(self.m_freq_h(entities)*months + self.m_phi_h(entities))
            emb += self.d_amps_h(entities)*self.time_nl(self.d_freq_h(entities)*days + self.d_phi_h(entities))
        else:
            emb = self.y_amps_t(entities) * self.time_nl(self.y_freq_t(entities) * years + self.y_phi_t(entities))
            emb += self.m_amps_t(entities) * self.time_nl(self.m_freq_t(entities) * months + self.m_phi_t(entities))
            emb += self.d_amps_t(entities) * self.time_nl(self.d_freq_t(entities) * days + self.d_phi_t(entities))

        return emb

    def get_Embeddings(self, heads,rels, tails, years, months, days, intervals = None):
        years = years.view(-1,1)
        months = months.view(-1,1)
        days = days.view(-1,1)

        h_embs1 = self.ent_encoder(heads)
        r_embs1 = self.rel_encoder(rels)
        t_embs1 = self.ent_encoder(tails)

        h_embs2 = self.ent_encoder(tails)
        r_embs2 = self.rel_encoder_i(rels)
        t_embs2 = self.ent_encoder(heads)

        h_embs1 = torch.cat((h_embs1, self.get_time_embedd(heads, years, months, days, "head")), 1)
        t_embs1 = torch.cat((t_embs1, self.get_time_embedd(tails, years, months, days, "tail")), 1)
        h_embs2 = torch.cat((h_embs2, self.get_time_embedd(tails, years, months, days, "head")), 1)
        t_embs2 = torch.cat((t_embs2, self.get_time_embedd(heads, years, months, days, "tail")), 1)

        return h_embs1, r_embs1, t_embs1, h_embs2, r_embs2, t_embs2

    def forward(self, heads, rels, tails, years, months, days):
        h_embs1, r_embs1, t_embs1, h_embs2, r_embs2, t_embs2 = self.get_Embeddings(heads, rels, tails, years, months, days)
        scores = ((h_embs1 * r_embs1) * t_embs1 + (h_embs2 * r_embs2) * t_embs2) / 2.0
        scores = F.dropout(scores, p=self.params.dropout, training=self.training)
        scores = torch.sum(scores, dim=1)
        return scores

    