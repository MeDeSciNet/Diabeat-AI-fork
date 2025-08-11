import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/routes/guest/auth_state.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key});

  @override
  AuthState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends AuthState<RegisterPage> {
  String? _usernameErr;
  late String _username;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: util.backAppBar(context),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Form(
            key: formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Spacer(flex: 1),
                const Text(
                  '歡迎加入 !',
                  style: TextStyle(fontSize: 35),
                  textAlign: TextAlign.center,
                ),
                const Spacer(flex: 1),
                buildEmailField(),
                const SizedBox(height: 20),
                TextFormField(
                  validator: _usernameValidator,
                  autovalidateMode: AutovalidateMode.onUnfocus,
                  onSaved: (newValue) => _username = newValue!,
                  forceErrorText: _usernameErr,
                  textInputAction: TextInputAction.next,
                  decoration: InputDecoration(
                    labelText: 'Username',
                    border: const OutlineInputBorder(),
                  ),
                  onChanged: (value) {
                    if (_usernameErr != null) {
                      setState(() => _usernameErr = null);
                    }
                  },
                ),
                const SizedBox(height: 20),
                TextFormField(
                  validator: passwordValidator,
                  autovalidateMode: AutovalidateMode.onUnfocus,
                  onSaved: (newValue) => password = newValue!,
                  keyboardType: TextInputType.visiblePassword,
                  textInputAction: TextInputAction.done,
                  obscureText: passwordObscured,
                  decoration: passwordDecoration(),
                ),
                const Spacer(flex: 2),
                Row(
                  children: [
                    buildScanButton(),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: waiting ? null : _tryRegister,
                        style: util.filledPageButtonStyle(),
                        icon: const Icon(Icons.create),
                        label: const Text('註冊'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String? _usernameValidator(String? value) {
    if (value == null || value.isEmpty) {
      return 'Username 不能為空';
    }

    if (value.length > 30) {
      return 'Username 長度應不超過 30';
    }

    return null;
  }

  Future<void> _tryRegister() async {
    if (!formState.validate()) return;
    formState.save();

    setState(() => waiting = true);

    final result = await request.register(
      context,
      email: email,
      username: _username,
      password: password,
    );
    if (!mounted) return;

    if (result.ok) {
      Navigator.of(
        context,
        rootNavigator: true,
      ).pushNamedAndRemoveUntil('/home', (route) => false);
    } else {
      setState(() {
        waiting = false;
        if (!result.haveData) return;

        final data = result.dataAsMap;
        if (data.containsKey('email')) {
          emailErr = switch (data['email'][0]) {
            'Enter a valid email address.' => 'Email 格式不正確',
            'custom user with this email already exists.' => '此 Email 已被使用',
            _ => '錯誤',
          };
        }
        if (data.containsKey('username')) {
          _usernameErr = switch (data['username'][0]) {
            'custom user with this username already exists.' =>
              '此 Username 已被使用',
            _ => '錯誤',
          };
        }
      });
    }
  }
}
