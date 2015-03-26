import theano
import theano.tensor as T
import numpy as np

import data


def floatX(X):
    return np.asarray(X, dtype=theano.config.floatX)


def build_model(window_size=19, hidden_layer_size=100, learning_rate=0.03,
                L1_reg=0.00, L2_reg=0.0001):
    print '... loading model (%d-%d-%d)' % (window_size*20, hidden_layer_size, 3)

    def init_weights_sigmoid(shape):
        return theano.shared(
            floatX(np.random.uniform(
                low=-np.sqrt(6./(shape[0]+shape[1]))*4.,
                high=np.sqrt(6./(shape[0]+shape[1]))*4.,
                size=shape)),
            borrow=True
        )

    def init_weights(shape):
        values = np.random.randn(*shape)*0.01
        return theano.shared(floatX(values), borrow=True)

    def init_bias(shape):
        values = np.zeros((shape,), dtype=theano.config.floatX)
        return theano.shared(values, borrow=True)

    def sgd(cost, params):
        grads = T.grad(cost=cost, wrt=params)
        updates = []
        for param, grad in zip(params, grads):
            updates.append([param, param - grad * learning_rate])
        return updates

    def model(X, w_h, b_h, w_o, b_o):
        h = T.nnet.sigmoid(T.dot(X, w_h) + b_h)
        return T.nnet.softmax(T.dot(h, w_o) + b_o)

    X = T.matrix()
    Y = T.matrix()

    input_layer_size = window_size * 20
    output_layer_size = 3
    w_h = init_weights_sigmoid((input_layer_size, hidden_layer_size))
    b_h = init_bias(hidden_layer_size)
    w_o = init_weights((hidden_layer_size, output_layer_size))
    b_o = init_bias(output_layer_size)

    py_x = model(X, w_h, b_h, w_o, b_o)
    y_pred = T.argmax(py_x, axis=1)

    NLL = -T.mean(T.log(py_x)[T.arange(Y.shape[0]), T.argmax(Y, axis=1)])
    L1 = T.sum(abs(w_h)) + T.sum(abs(w_o))
    L2_sqr = T.sum((w_h**2)) + T.sum((w_o**2))
    cost = NLL + L1_reg * L1 + L2_reg * L2_sqr
    params = [w_h, b_h, w_o, b_o]
    updates = sgd(cost, params)

    start = T.lscalar()
    end = T.lscalar()

    train = theano.function(
        inputs=[start, end],
        outputs=y_pred,
        updates=updates,
        givens={
            X: X_train[start:end],
            Y: Y_train[start:end]
        },
        allow_input_downcast=True
    )

    predict = theano.function(
        inputs=[start, end],
        outputs=y_pred,
        givens={
            X: X_test[start:end],
        },
        allow_input_downcast=True
    )

    return train, predict


def train_model(num_epochs=10, batch_size=1):
    print '... training model (batch_size = %d)' % batch_size

    m_train = X_train.get_value(borrow=True).shape[0]
    m_test = X_test.get_value(borrow=True).shape[0]

    starts = range(0, m_train, batch_size)
    ends = range(batch_size, m_train, batch_size)

    Q3 = []
    for i in range(num_epochs):
        for start, end in zip(starts, ends):
            Y_predicted = train(start, end)
            Y_desired = np.argmax(Y_train.get_value(borrow=True)[start:end], axis=1)
            Q3.append(np.mean(Y_desired == Y_predicted))
        Q3_train = np.mean(Q3)
        Y_predicted = predict(0, m_test)
        Y_desired = np.argmax(Y_test.get_value(borrow=True), axis=1)
        Q3_test = np.mean(Y_desired == Y_predicted)
        print 'epoch %2d/%d. Q3_train: %.3f%%, Q3_test: %.3f%%' % \
            (i+1, num_epochs, Q3_train*100., Q3_test*100.)


def shared_dataset(data_xy, borrow=True):
    data_x, data_y = data_xy
    shared_x = theano.shared(floatX(data_x), borrow=borrow)
    shared_y = theano.shared(floatX(data_y), borrow=borrow)
    return shared_x, shared_y


if __name__ == '__main__':
    train_file = 'data/training10.data'
    test_file = 'data/test10.data'
    window_size = 19

    hidden_layer_size = 100
    learning_rate = 0.03

    num_epochs = 10
    batch_size = 20

    X_train, Y_train = shared_dataset(data.load(train_file, window_size=window_size))
    X_test, Y_test = shared_dataset(data.load(test_file, window_size=window_size))

    train, predict = build_model(
        window_size=window_size,
        hidden_layer_size=hidden_layer_size,
        learning_rate=learning_rate
    )

    train_model(num_epochs=num_epochs, batch_size=batch_size)

    print '\nDone!'