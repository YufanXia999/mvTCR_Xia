import operator
from tcr_embedding.models.pertubation_prediction import run_scgen_cross_validation


def report_modulation_prediction(adata, model, optimization_mode_params, batch_size, epoch, comet):
    summary = run_scgen_cross_validation(adata, optimization_mode_params['column_fold'],
                                         model, optimization_mode_params['column_perturbation'],
                                         optimization_mode_params['indicator_perturbation'],
                                         optimization_mode_params['column_cluster'],
                                         batch_size)
    score = summary['avg_r_squared']
    if comet is not None:
        for key, value in summary.items():
            if key == 'avg_r_squared':
                comet.log_metric(key, value, step=int(epoch), epoch=epoch)
            else:
                comet.log_metrics(value, prefix=key, step=int(epoch), epoch=epoch)
    return score, operator.gt
