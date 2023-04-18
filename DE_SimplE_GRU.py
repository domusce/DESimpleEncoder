import torch
import torch.nn as nn
import numpy as np
import torch.nn.functional as F
# from params import Params
# from dataset import Dataset


Glove_path = 'glove/glove.6B.300d.txt'
class DE_SimplE_GRU(nn.Module):
    def __init__(self,dataset, params, hidden_size=100, pretrained_vocab=None,
                 pretrained_emb = None):
        super(DE_SimplE_GRU, self).__init__()

        self.dataset = dataset
        self.params = params
        self.hidden_size = hidden_size

        self.init_embeddings(pretrained_vocab, pretrained_emb)

        self.ent_embs_h = nn.Embedding(dataset.numEnt(), params.s_emb_dim).cuda()
        self.ent_embs_t = nn.Embedding(dataset.numEnt(), params.s_emb_dim).cuda()
        self.rel_embs_f = nn.Embedding(dataset.numRel(), params.s_emb_dim+params.t_emb_dim).cuda()
        self.rel_embs_i = nn.Embedding(dataset.numRel(), params.s_emb_dim+params.t_emb_dim).cuda()

        self.ent_encoder_h = nn.GRU(params.s_emb_dim, self.hidden_size, batch_first=True).cuda()
        self.ent_encoder_t = nn.GRU(params.s_emb_dim, self.hidden_size, batch_first=True).cuda()
        self.rel_encoder_f = nn.GRU(params.s_emb_dim+params.t_emb_dim, self.hidden_size, batch_first=True).cuda()
        self.rel_encoder_i = nn.GRU(params.s_emb_dim+params.t_emb_dim, self.hidden_size, batch_first=True).cuda()

        self.create_time_embedd()

        self.time_nl = torch.sin

        nn.init.xavier_uniform_(self.ent_embs_h.weight)
        nn.init.xavier_uniform_(self.ent_embs_t.weight)
        nn.init.xavier_uniform_(self.rel_emb_f.weight)
        nn.init.xavier_uniform_(self.rel_emb_i.weight)
    
    def init_embeddings(self, pretrained_vocab = None, pretrained_emb = None):
        ...
        self.word_ent_embedd = {}
        self.word_rel_embedd = {}
        if pretrained_vocab is None or pretrained_vocab is None:
            with open(Glove_path, encoding='utf-8') as glove:
                for line in glove:
                    word, vec = line.split(' ', 1)
                    if word in self.dataset.ent2id:
                        self.word_ent_embedd[self.dataset.ent2id[word]] = np.fromstring(vec, sep=' ')
                    if word in self.dataset.rel2id:
                        self.word_rel_embedd[self.dataset.rel2id[word]] = np.fromstring(vec, sep=' ')

        ent_uninitialized = [word for word in self.dataset.ent2id.values() if not word in self.word_ent_embedd]
        rel_uninitialized = [word for word in self.dataset.rel2id.values() if not word in self.word_rel_embedd]

        for word in ent_uninitialized:
            self.word_ent_embedd[word] = np.random.normal(size=300)
        
        for word in rel_uninitialized:
            self.word_rel_embedd[word] = np.random.normal(size=300)

        self.ent_embedd_matrix = np.zeros(len(self.word_ent_embedd), 300)
        self.rel_embedd_matrix = np.zeros(len(self.word_rel_embedd), 300)

        for word in self.word_ent_embedd:
            self.ent_embedd_matrix[word] = self.word_ent_embedd[word]
        
        for word in self.word_rel_embedd:
            self.rel_embedd_matrix[word] = self.word_rel_embedd[word]

    def create_time_embedd(self):
        # frequency embeddings for the entities
        self.m_freq_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.m_freq_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.d_freq_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.d_freq_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.y_freq_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.y_freq_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()

        # phi embeddings for the entities
        self.m_phi_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.m_phi_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.d_phi_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.d_phi_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.y_phi_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.y_phi_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()

        # frequency embeddings for the entities
        self.m_amps_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.m_amps_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.d_amps_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.d_amps_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.y_amps_h = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()
        self.y_amps_t = nn.Embedding(self.dataset.numEnt(), self.params.t_emb_dim).cuda()

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

    def get_time_embedd(self, entities, years, months, days, h_or_t):
        if h_or_t == "head":
            emb  = self.y_amps_h(entities) * self.time_nl(self.y_freq_h(entities) * years  + self.y_phi_h(entities))
            emb += self.m_amps_h(entities) * self.time_nl(self.m_freq_h(entities) * months + self.m_phi_h(entities))
            emb += self.d_amps_h(entities) * self.time_nl(self.d_freq_h(entities) * days   + self.d_phi_h(entities))
        else:
            emb  = self.y_amps_t(entities) * self.time_nl(self.y_freq_t(entities) * years  + self.y_phi_t(entities))
            emb += self.m_amps_t(entities) * self.time_nl(self.m_freq_t(entities) * months + self.m_phi_t(entities))
            emb += self.d_amps_t(entities) * self.time_nl(self.d_freq_t(entities) * days   + self.d_phi_t(entities))
            
        return emb

    def getEncoder(self, heads, rels, tails, years, months, days, intervals = None):
        years = years.view(-1,1)
        months = months.view(-1,1)
        days = days.view(-1,1)

        h_embs1 = self.ent_embs_h(heads)
        r_embs1 = self.rel_embs_f(rels)
        t_embs1 = self.ent_embs_t(tails)
        h_embs2 = self.ent_embs_h(tails)
        r_embs2 = self.rel_embs_i(rels)
        t_embs2 = self.ent_embs_t(heads)
        
        h_embs1 = torch.cat((h_embs1, self.get_time_embedd(heads, years, months, days, "head")), 1)
        t_embs1 = torch.cat((t_embs1, self.get_time_embedd(tails, years, months, days, "tail")), 1)
        h_embs2 = torch.cat((h_embs2, self.get_time_embedd(tails, years, months, days, "head")), 1)
        t_embs2 = torch.cat((t_embs2, self.get_time_embedd(heads, years, months, days, "tail")), 1)


        h_s1, h_enc_s1 = self.ent_encoder_h(h_embs1)
        r_s1, r_enc_s1 = self.rel_encoder_f(r_embs1)
        t_s1, t_enc_s1 = self.ent_encoder_t(t_embs1)

        h_s2, h_enc_s2 = self.ent_encoder_h(h_embs2)
        r_s2, r_enc_s2 = self.rel_encoder_f(r_embs2)
        t_s2, t_enc_s2 = self.ent_encoder_t(t_embs2) 

        return h_s1, r_s1, t_s1, h_s2, r_s2, t_s2
        # return h_enc_s1, r_enc_s1, t_enc_s1, h_enc_s2, r_enc_s2, t_enc_s2
    
    def forward(self, heads, rels, tails, years, months, days):
        h_enc_s1, r_enc_s1, t_enc_s1, h_enc_s2, r_enc_s2, t_enc_s2 = self.getEncoder(heads, rels, tails, years, months, days)
        scores = ((h_enc_s1*r_enc_s1)*t_enc_s1 + (h_enc_s2*r_enc_s2)*t_enc_s2)/2.0
        scores = F.dropout(scores, p=self.params.dropout, training=self.training)
        scores = torch.sum(scores, dim=1)
        return scores