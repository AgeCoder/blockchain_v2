import hashlib
import json




def crypto_hash(*args):

    stringified_args = sorted(map(lambda data: json.dumps(data) ,args))

    joinined_args = ''.join(stringified_args)

    return hashlib.sha256(joinined_args.encode('utf-8')).hexdigest()


def main():
    print(crypto_hash('three',[79],{1:40},'one',2))

if __name__ == '__main__':
    main()