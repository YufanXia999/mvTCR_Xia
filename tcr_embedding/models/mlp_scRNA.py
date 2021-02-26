from .mlp import MLP


def build_mlp_encoder(params, xdim, hdim):
	return MLP(xdim, hdim, params['gene_hidden'], params['activation'], params['activation'], params['dropout'],
			   params['batch_norm'], regularize_last_layer=True)


def build_mlp_decoder(params, xdim, hdim):
	return MLP(hdim*2, xdim, params['gene_hidden'][::-1], params['activation'], params['output_activation'],
			   params['dropout'], params['batch_norm'], regularize_last_layer=False)
