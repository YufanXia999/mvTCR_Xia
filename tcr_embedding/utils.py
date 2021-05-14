import numpy as np
from tqdm import tqdm
from sklearn.model_selection import GroupShuffleSplit
import scanpy as sc
from .constants import HIGH_COUNT_ANTIGENS, ANTIGEN_COLORS


def aa_encoding(adata, read_col, ohe_col=None, label_col=None, length_col=None, pad=False, aa_to_id=None, start_end_symbol=True):
	"""
	Encoding of protein or nucleotide sequence inplace, either one-hot-encoded or as index labels and/or one-hot-encoding
	:param adata: adata file
	:param read_col: str column containing sequence
	:param ohe_col: None or str, if str column to write one-hot-encoded sequence into
	:param label_col: None or str, if str then write labels as index to this column
	:param length_col: str column None or str, if str write sequence length into this column
	:param pad: bool or int value, if int value then the sequence will be pad to this value,
				if True then pad_len will be determined by taking the longest sequence length in adata
	:param aa_to_id: None or dict, None will create a dict in this code, dict should contain {aa: index}
	:param start_end_symbol: bool, add a start '<' and end '>' symbol to each sequence
	:return:
	"""
	if label_col is None and ohe_col is None:
		raise AssertionError('Specify at least one column to write: ohe_col or label_col')

	if start_end_symbol:
		adata.obs[read_col] = '<' + adata.obs[read_col].astype('str') + '>'
		if type(pad) is int:
			pad += 2

	if length_col:
		adata.obs[length_col] = adata.obs[read_col].str.len()

	# Padding if specified
	if type(pad) is int:
		sequence_col = adata.obs[read_col].str.ljust(pad, '_')
	elif pad:
		pad_len = adata.obs[read_col].str.len().max()
		sequence_col = adata.obs[read_col].str.ljust(pad_len, '_')
	else:
		sequence_col = adata.obs[read_col]

	# tokenize each character, i.e. create list of characters
	aa_tokens = sequence_col.apply(lambda x: list(x))

	# dict containing aa name as key and token-id as value
	if aa_to_id is None:
		unique_aa_tokens = sorted(set([x for sublist in aa_tokens for x in sublist]))
		aa_to_id = {aa: id_ for id_, aa in enumerate(unique_aa_tokens)}

	# convert aa to token_id (i.e. unique integer for each aa)
	token_ids = [[aa_to_id[token] for token in aa_token] for aa_token in aa_tokens]

	# convert token_ids to one-hot
	if ohe_col is not None:
		one_hot = [np.zeros((len(aa_token), len(aa_to_id))) for aa_token in aa_tokens]
		for x_seq, token_id_seq in zip(one_hot, token_ids):
			for x, token_id in zip(x_seq, token_id_seq):
				x[token_id] = 1.0
		adata.obs[ohe_col] = one_hot
		adata.obsm[ohe_col] = np.stack(one_hot)

	# If specified write label as index sequence
	if label_col is not None:
		token_ids = [np.array(token_id) for token_id in token_ids]
		adata.obs[label_col] = token_ids
		adata.obsm[label_col] = np.stack(token_ids)

	adata.uns['aa_to_id'] = aa_to_id


def stratified_group_shuffle_split(df, stratify_col, group_col, val_split, random_seed=42):
	"""
	https://stackoverflow.com/a/63706321
	Split the dataset into train and test. To create a val set, execute this code twice to first split test+val and test
	and then split the test and val.

	The splitting tries to improve splitting by two properties:
	1) Stratified splitting, so the label distribution is roughly the same in both sets, e.g. antigen specificity
	2) Certain groups are only in one set, e.g. the same clonotypes are only in one set, so the model cannot peak into similar sample during training.

	If there is only one group to a label, the group is defined as training, else as test sample, the model never saw this label before.

	The outcome is not always ideal, i.e. the label distribution may not , as the labels within a group is heterogeneous (e.g. 2 cells from the same clonotype have different antigen labels)
	Also see here for the challenges: https://github.com/scikit-learn/scikit-learn/issues/12076

	:param df: pd.DataFrame containing the data to split
	:param stratify_col: str key for the column containing the classes to be stratified over all sets
	:param group_col: str key for the column containing the groups to be kept in the same set
	"""
	groups = df.groupby(stratify_col)
	all_train = []
	all_test = []
	for group_id, group in tqdm(groups):
		# if a group is already taken in test or train it must stay there
		group = group[~group[group_col].isin(all_train + all_test)]
		# if group is empty
		if group.shape[0] == 0:
			continue

		if len(group) > 1:
			train_inds, test_inds = next(
				GroupShuffleSplit(test_size=val_split, n_splits=1, random_state=random_seed).split(group, groups=group[
					group_col]))
			all_train += group.iloc[train_inds][group_col].tolist()
			all_test += group.iloc[test_inds][group_col].tolist()
		# if there is only one clonotype for this particular label
		else:
			all_train += group[group_col].tolist()

	train = df[df[group_col].isin(all_train)]
	test = df[df[group_col].isin(all_test)]

	return train, test


def plot_umap(adata, title):
	adata.obs['binding_name'] = adata.obs['binding_name'].astype(str)
	sc.pp.neighbors(adata, use_rep='X')
	sc.tl.umap(adata)
	fig_donor = sc.pl.umap(adata, color='donor', title=title, return_fig=True)
	fig_donor.tight_layout()
	fig_clonotype = sc.pl.umap(adata, color='clonotype', title=title, return_fig=True)
	fig_clonotype.tight_layout()
	fig_antigen = sc.pl.umap(adata, color='binding_name', groups=HIGH_COUNT_ANTIGENS + ['no_data'], palette=ANTIGEN_COLORS, title=title, return_fig=True)
	fig_antigen.tight_layout()
	fig_antigen.set_size_inches(12, 4.8)

	return fig_donor, fig_clonotype, fig_antigen


def plot_umap_list(adata, title, color_groups):
	"""
	Plots UMAPS based with different coloring groups
	:param adata: Adata Object containing a latent space embedding
	:param title: Figure title
	:param color_groups: Column name in adata.obs used for coloring the UMAP
	:return:
	"""
	print('p1----------------------')
	sc.pp.neighbors(adata, use_rep='X')
	print('p2----------------------')
	sc.tl.umap(adata)
	print('p3----------------------')
	figures = []
	for group in color_groups:
		print('##########################')
		print(group)
		fig = sc.pl.umap(adata, color=group, title=title, return_fig=True)
		fig.tight_layout()
		figures.append(fig)
	return figures
