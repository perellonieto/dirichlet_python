import logging
import numpy as np

from sklearn.base import BaseEstimator, RegressorMixin

from dirichlet.calib.fulldirichlet import FullDirichletCalibrator
from dirichlet.calib.diagdirichlet import DiagonalDirichletCalibrator
from dirichlet.calib.fixeddirichlet import FixedDiagonalDirichletCalibrator


class DirichletCalibrator(BaseEstimator, RegressorMixin):
    def __init__(self, matrix_type='full', l2=0.0, comp_l2=False):
        if matrix_type not in ['full', 'diagonal', 'fixed_diagonal']:
            raise(ValueError)

        self.matrix_type = matrix_type
        self.l2 = l2
        self.comp_l2 = comp_l2

    def fit(self, X, y, X_val=None, y_val=None, **kwargs):

        if self.matrix_type == 'diagonal':
            self.calibrator_ = DiagonalDirichletCalibrator(l2=self.l2)
        elif self.matrix_type == 'fixed_diagonal':
            self.calibrator_ = FixedDiagonalDirichletCalibrator(l2=self.l2)
        else:
            self.calibrator_ = FullDirichletCalibrator(l2=self.l2,
                                                       comp_l2=self.comp_l2)

        _X = np.copy(X)
        if len(X.shape) == 1:
            _X = np.vstack(((1-_X), _X)).T

        _X_val = X_val
        if X_val is not None:
            _X_val = np.copy(X_val)
            if len(X_val.shape) == 1:
                _X_val = np.vstack(((1-_X_val), _X_val)).T

        self.calibrator_ = self.calibrator_.fit(_X, y, X_val=_X_val,
                                                y_val=y_val, **kwargs)
        return self


    @property
    def coef_(self):
        return self.calibrator_.coef_


    @property
    def intercept_(self):
        return self.calibrator_.intercept_


    def predict_proba(self, S):

        _S = np.copy(S)
        if len(S.shape) == 1:
            _S = np.vstack(((1-_S), _S)).T
            return self.calibrator_.predict_proba(_S)[:,1]

        return self.calibrator_.predict_proba(_S)

    def predict(self, S):

        _S = np.copy(S)
        if len(S.shape) == 1:
            _S = np.vstack(((1-_S), _S)).T
            return self.calibrator_.predict(_S)[:,1]

        return self.calibrator_.predict(_S)
