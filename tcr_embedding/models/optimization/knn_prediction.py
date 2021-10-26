import operator

from tcr_embedding.evaluation.WrapperFunctions import get_model_prediction_function
from tcr_embedding.evaluation.Imputation import run_imputation_evaluation


def report_knn_prediction(adata, model, optimization_mode_params, batch_size, epoch, comet):
    """
    Report the objective metric of the 10x dataset for hyper parameter optimization.
    :param epoch: epoch number for logging
    :return: Reports externally to comet, saves model.
    """
    test_embedding_func = get_model_prediction_function(model, batch_size=batch_size)
    try:
        summary = run_imputation_evaluation(adata, test_embedding_func, query_source='val',
                                            use_non_binder=True, use_reduced_binders=True,
                                            label_pred=optimization_mode_params['prediction_column'])
    except:
        print(f'kNN did not work')
        return

    metrics = summary['knn']

    if comet is not None:
        for antigen, metric in metrics.items():
            if antigen != 'accuracy':
                comet.log_metrics(metric, prefix=antigen, epoch=epoch)
            else:
                comet.log_metric('accuracy', metric, epoch=epoch)
    return metrics['weighted avg']['f1-score'], operator.gt
