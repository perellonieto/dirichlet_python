from __future__ import division

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import label_binarize
from sklearn.metrics import log_loss

from scipy.optimize import fmin_l_bfgs_b


class DiagonalDirichletCalibrator(BaseEstimator, RegressorMixin):
    def __init__(self):
        self.coef_ = None
        self.intercept_ = None

    def fit(self, X, y, *args, **kwargs):
        eps = np.finfo(X.dtype).eps
        X_ = np.log(np.clip(X, eps, 1-eps))

        X_ = np.hstack((X_, np.ones((len(X), 1))))

        k = len(np.unique(y))
        target = label_binarize(y, range(k))

        weights_0 = np.zeros((k+1, k-1))
        weights_0[np.diag_indices(k-1)] = np.random.rand(k-1)
        weights_0[k-1] = np.random.rand(k-1) * -1
        weights_0[k] = np.random.randn(k-1)

        weights_0 = weights_0.ravel()

        dims = (k+1, k-1)
        diag_ravel_ind = np.ravel_multi_index(np.diag_indices(k-1), dims)

        k_ind = [np.ones(k-1, dtype=int)*(k-1), np.arange(k-1)]
        k_ravel_ind = np.ravel_multi_index(k_ind, dims)

        intercept_ind = [np.ones(k-1, dtype=int)*k, np.arange(k-1)]
        intercept_ravel_ind = np.ravel_multi_index(intercept_ind, dims)

        bounds = []
        for ind, _ in enumerate(weights_0):
            if ind in diag_ravel_ind:
                bounds.append((0, np.inf))
            elif ind in k_ravel_ind:
                bounds.append((-np.inf, 0))
            elif ind in intercept_ravel_ind:
                bounds.append((-np.inf, np.inf))
            else:
                bounds.append((0, 0))

        weights, _, _ = fmin_l_bfgs_b(
            _objective,
            fprime=_grad,
            x0=weights_0,
            args=(X_, target),
            bounds=bounds
        )

        self.weights_ = weights.reshape(-1, k-1)
        self.coef_ = self.weights_.transpose()[:, :-1]
        self.intercept_ = self.weights_.transpose()[:, -1]
        return self

    def predict_proba(self, S):
        eps = np.finfo(S.dtype).eps
        S_ = np.log(np.clip(S, eps, 1-eps))
        S_ = np.hstack((S_, np.ones((len(S), 1))))
        return _calculate_outputs(self.weights_, S_)

    def predict(self, S):
        return self.predict_proba(S)


def _objective(params, *args):
    (X, y) = args
    weights = params.reshape(-1, 2)
    outputs = _calculate_outputs(weights, X)
    loss = log_loss(y, outputs, normalize=False)
    return loss


def _grad(params, *args):
    (X, y) = args
    weights = params.reshape(-1, 2)
    outputs = _calculate_outputs(weights, X)

    k = len(weights) - 1

    grad = np.zeros_like(weights)

    s = outputs[range(len(y)), np.argmax(y, axis=1)]

    for i in range(k + 1):
        for j in range(k - 1):
            grad[i, j] = np.sum((s - 1) * X[:, i])

    return grad.ravel()


def _calculate_outputs(weights, X):
    k = len(weights) - 1
    mul = np.zeros((len(X), k))
    mul[:, :k-1] = np.dot(X, weights)
    return _softmax(mul)


def _softmax(X):
    """Compute the softmax of matrix X in a numerically stable way."""
    shiftx = X - np.max(X, axis=1).reshape(-1, 1)
    exps = np.exp(shiftx)
    return exps / np.sum(exps, axis=1).reshape(-1, 1)


class DirichletCalibrator(BaseEstimator, RegressorMixin):
    def __init__(self):
        self.calibrator_ = None

    def fit(self, X, y, *args, **kwargs):
        n = len(y)

        eps = np.finfo(X.dtype).eps
        X = np.log(np.clip(X, eps, 1-eps))

        self.calibrator_ = LogisticRegression(
            C=99999999999,
            multi_class='multinomial', solver='saga'
        ).fit(X, y, *args, **kwargs)

        return self

    def predict_proba(self, S):
        eps = np.finfo(S.dtype).eps
        S = np.log(np.clip(S, eps, 1-eps))
        return self.calibrator_.predict_proba(S)

    def predict(self, S):
        eps = np.finfo(S.dtype).eps
        S = np.log(np.clip(S, eps, 1-eps))
        return self.calibrator_.predict(S)