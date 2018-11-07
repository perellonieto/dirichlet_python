import logging
from sklearn.base import BaseEstimator, RegressorMixin

import numpy as np
from .multinomial import MultinomialRegression
from ..utils import clip_for_log
from sklearn.metrics import log_loss


class FullDirichletCalibrator(BaseEstimator, RegressorMixin):
    def __init__(self, l2=0.0, comp_l2=False, weights_init=None):
    
        """
        Params:
            weights_init: (nd.array) weights used for initialisation, if None then idendity matrix used. Shape = (n_classes - 1, n_classes + 1)
            l2: (float) regularization parameter (lambda)
            comp_l2: (bool) If true, then complementary L2 regularization used (off-diagonal regularization)
        """
    
        self.calibrator_ = None
        self.weights_ = weights_init  # Input weights for initialisation
        self.l2 = l2
        self.comp_l2 = comp_l2  # Complementary L2 regularization. (Off-diagonal regularization)
        
    def fit(self, X, y, X_val=None, y_val=None, *args, **kwargs):

        _X = np.copy(X)
        _X = np.log(clip_for_log(_X))

        if isinstance(self.l2, list):
            _X_val = np.copy(X_val)
            if len(_X_val.shape) == 1:
                _X_val = np.vstack(((1-_X_val), _X_val)).T
            _X_val = np.log(clip_for_log(_X_val))
            calibrators = []
            losses = []
            for l2 in self.l2:
                calibrators.append(MultinomialRegression(method='Full', l2=l2, comp_l2 = self.comp_l2, weights_0 = self.weights_).fit(_X, y,
                                                                    *args,
                                                                    **kwargs))
                losses.append(log_loss(y_val, calibrators[-1].predict_proba(_X_val)))

            lower_loss_index = np.argmin(losses)
            logging.debug('Best l2 regularization = {}'.format(self.l2[lower_loss_index]))
            self.calibrator_ = calibrators[lower_loss_index]
            self.l2 = self.l2[lower_loss_index]
        else:
            self.calibrator_ = MultinomialRegression(method='Full', l2=self.l2, 
                                                     comp_l2 = self.comp_l2, weights_0 = self.weights_).fit(_X, y, *args, **kwargs)

        return self

    @property
    def coef_(self):
        return self.calibrator_.coef_

    @property
    def intercept_(self):
        return self.calibrator_.intercept_

    def predict_proba(self, S):
        S = np.log(clip_for_log(S))
        return self.calibrator_.predict_proba(S)

    def predict(self, S):
        S = np.log(clip_for_log(S))
        return self.calibrator_.predict(S)
    
    def get_loss_reg(self, X, y):
        # Helper function for getting objective loss and regularization value.
        X = np.log(clip_for_log(X))
        return self.calibrator_.get_loss_reg(X, y)
        