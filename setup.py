#pip install git+ssh://git@github.com/dazarius/SDK.git --break-system-packages
from setuptools import setup, find_packages

setup(
    name='orbis_pay_sdk',
    version='1.1.9',
    description='OrbisPay SDK for ERC20/ERC721 and P2P smart contract interaction',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='dazay',
    license='MIT',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'web3>=6.0.0',
        'requests>=2.28.0',
        'solana>=0.36.0,<0.37.0',
        'anchorpy>=0.21.0',
        'jupiter-python-sdk>=0.0.2',
        'base58>=2.1.0',
    	'tonsdk', 
	    'httpx',
	    'tronpy',
	    'bit',
        'bip_utils',
        "tonutils",
        "websockets"
    ],
    python_requires='>=3.9',
)

